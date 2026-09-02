#!/usr/bin/env python3
"""Generate `.hitl/current-change.yaml` from the workflow catalog.

Lifted out of `ai/claude/start-change/SKILL.md` (#97). It lived as a 160-line heredoc inside a
markdown skill, which meant nothing could run it without first extracting it with `sed` — so every
test of it either did that dance or asserted against the source text instead of the behaviour. A
guard that reads code it never executes is how three features shipped unreachable here.

Usage:
  gen_change.py <workflow> <change_id> <branch> <hitl_version> <tier> \\
                <choices_path> <tier_set_by> <tier_reason>

Writes the change file to stdout. The caller redirects to a temp file and moves it into place only
on a clean exit, because a generator that dies partway through `> file` leaves a truncated change
file behind, and a truncated change file reads as "no active change" to the gate.
"""
import sys, os, json, yaml
from datetime import datetime, timezone

# ── stub mode (#97) ────────────────────────────────────────────────────────────────────────────
# Intake writes the change file BEFORE a plan exists, because the plan is produced by impact
# analysis, which runs after the requirement is agreed. The stub does three things: it persists the
# agreed requirement and definition of done so a session dying mid-intake does not lose the text
# everything downstream derives from, it gives the analysis its input, and it names the impact
# record so the blocking reference check has a subject.
#
# It deliberately does NOT satisfy `hitl_change_active`: no `current_step`, no `workflow` block, so
# source edits stay blocked through intake. That is right — there is no plan yet, so nothing has
# authorised an edit. An earlier draft of this comment claimed the opposite.
#
# It carries a PROVISIONAL tier of 3 — the strictest — so it fails closed if anything resolves
# criticality against it. `status: intake` exempts it from the plan checks, narrowly: check_skips
# blocks (INTAKE_NOT_EMPTY) if a change claims intake while carrying steps or skips, so the status
# cannot be used to un-certify work that has been planned.
if len(sys.argv) > 1 and sys.argv[1] == "--stub":
    if len(sys.argv) < 5:
        sys.exit("usage: gen_change.py --stub <change_id> <branch> <hitl_version>")
    _cid, _branch, _ver = sys.argv[2:5]
    _now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f'''schema_version: "2.0"
hitl_version: "{_ver}"

change_id: "{_cid}"
status: intake
expected_branch: "{_branch}"
opened_at: "{_now}"

# Provisional until impact analysis runs and a human confirms one (#97). check_skips blocks
# TIER_PROVISIONAL if this survives past intake, because the tier is proposed from findings and
# confirmed by a person, and a provisional value on a planned change means nobody confirmed it.
tier: 3
tier_provisional: true

# Filled by intake's restate-and-confirm, before anything is read or planned.
requirement:
  what: ""
  in_scope: []
  out_of_scope: []
  definition_of_done: []
  agreed_by: ""
  agreed_at: ""

# Written by impact analysis. A named record that is missing or empty BLOCKS: a second artifact is
# only safe when something notices its absence.
impact_record: ".hitl/impact/{_cid}.yaml"''')
    sys.exit(0)

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

# Carry the stub's durable fields forward (#97). Step 6 replaces `.hitl/current-change.yaml` with
# this output, so anything only the stub had is destroyed unless it is read back here: the agreed
# requirement and definition of done from Step 3b, and the impact-record pointer. Losing them means
# the definition-of-done coverage check has nothing to read and the record has nothing naming it.
_carry = {}
for _p in (".hitl/current-change.yaml",):
    if os.path.isfile(_p):
        try:
            _prev = yaml.safe_load(open(_p)) or {}
        except Exception:
            _prev = {}
        if isinstance(_prev, dict) and _prev.get("change_id") == change_id:
            for _f in ("requirement", "impact_record"):
                if _prev.get(_f):
                    _carry[_f] = _prev[_f]

# Catalog: one resolver, shared with the validator. This used to try two paths, neither of which is
# where an onboarded product repo keeps the file, so Step 6 failed with "workflows.yaml not found"
# for every real user while working perfectly in this source repo.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_skips import default_workflows as _dw          # noqa: E402
for p in (_dw(),):
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

# `not_applicable` (#97): the RULES excluded the step, which is not a person declining it. The step
# is still present in the plan with status `skipped` and still carries a record — check_skips has no
# clean shape for a step that is neither present nor recorded. Omitting this was why every
# right-sized change died here with no change file: the sizer produced a disposition the generator
# refused, and no test covered the generator with a rules-excluded choice.
STATUS_FOR = {"defer": "skipped", "decline": "skipped", "starter": "starter",
              "not_applicable": "skipped"}

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
    lines.append(f'    - {{ n: {q(s["n"])}, key: {q(s["key"])}, label: {q(s["label"])}, phase: {q(s["phase"])}, '
                 f'status: {st}' + (f', command: {q(s["command"])}' if s.get("command") else '') + ' }')

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
lines += [f'  command: {q(first["command"])}'] if first.get("command") else []  # statusline (#100)

# The stub's durable fields, re-emitted so Step 6 does not destroy them (#97).
if _carry:
    lines.append('')
    lines.append(yaml.safe_dump(_carry, sort_keys=False, default_flow_style=False).rstrip())

out = "\n".join(lines)
# Refuse to hand the wrapper something it cannot parse. The guard downstream checks exit status and
# non-emptiness; only this check can catch a file that is both and still invalid.
try:
    yaml.safe_load(out)
except yaml.YAMLError as e:
    sys.exit(f"generated change file is not valid YAML ({e.__class__.__name__}) — refusing to emit it.")
print(out)
