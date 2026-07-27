#!/usr/bin/env python3
"""First Pass (FR-29) skip-ledger validator — fail-closed.

Enforces the load-bearing invariants of the skip-with-record model against a `.hitl/current-change.yaml`
(and the workflow catalog for criticality). The non-waivable core (a green suite is not acceptance — these
are asserted by MUTATION in the test-plan):

  - SILENT_SKIP     a step marked skipped/starter has no complete record        (CR-3)  [non-waivable]
  - FLOOR_NO_ACK    a floor skip has no accountable-role ack                     (CR-5)  [non-waivable]
  - FLOOR_NO_WAIVER a floor skip mapping to a hard gate has no linked waiver     (CR-4)  [non-waivable]
  - NO_OMIT         a no_omit step (TDD) was deferred/declined, not thinned      (CR-6)  [non-waivable]

Plus consistency/quality checks: LEDGER_STEPS, STARTER_MARK, ROLLUP, and (catalog lint) CRIT_MONOTONIC.

Exit 0 = clean; exit 2 = blockers. Style mirrors #10's fail-closed validator + FR-28 `validate_skips`.
"""
from __future__ import annotations
import os
import sys


def _strict_load(path):
    """Parse YAML rejecting DUPLICATE keys — a forged ledger must not hide a skipped floor step behind a
    second `workflow:`/`skips:` key that PyYAML would collapse last-wins (round-4 LOW-4). Raises on a dup."""
    import yaml

    class _L(yaml.SafeLoader):
        pass

    def _no_dup(loader, node, deep=False):
        m = {}
        for kn, vn in node.value:
            k = loader.construct_object(kn, deep=deep)
            if k in m:
                raise yaml.constructor.ConstructorError(None, None, f"duplicate key {k!r}", kn.start_mark)
            m[k] = loader.construct_object(vn, deep=deep)
        return m

    _L.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _no_dup)
    with open(path) as f:
        return yaml.load(f, Loader=_L)


CRIT_ORDER = {"ceremony": 0, "standard": 1, "floor": 2}
DISPOSITIONS = {"defer", "decline", "starter"}
# The ONLY valid step statuses. Anything else is a fail-open vector (a floor step hidden behind an
# unknown status like "declined") — so an unrecognized status is a non-waivable BLOCK (round-1 CRIT-2).
VALID_STATUSES = {"done", "current", "open", "skipped", "starter"}
# A lightening status: the step was skipped/thinned, so it REQUIRES a complete record.
LIGHTENED_STATUSES = {"skipped", "starter"}
# Floor steps whose skip ALSO needs a linked waiver because they map to a fail-closed / merge-blocking
# gate (conventions/reviews/QA/security/infra/pentest). deploy/promote are irreversible OPS floor —
# ack_by is their control, there is no CI gate to waive. (round-1 HIGH-4: real dev-workflow keys, no
# dead entries.)
HARD_GATE_STEPS = {"conventions", "qa_verify", "arch_review", "integration_verify", "iac",
                   "security_review", "sec_design", "cve_audit", "pentest", "manifest_validate"}
# Non-waivable finding codes — the framework's guarantee under First Pass. A mismatch fails CLOSED.
NON_WAIVABLE = {"SILENT_SKIP", "FLOOR_NO_ACK", "FLOOR_NO_WAIVER", "NO_OMIT",
                "UNKNOWN_STEP", "INVALID_STATUS", "INVALID_TIER", "MALFORMED", "CRIT_MONOTONIC"}
STARTER_MARKER = "needs-enhancement"


def _list(x):   return x if isinstance(x, list) else []
def _str(v):    return v if isinstance(v, str) else ""


_CRIT_BY_RANK = {v: k for k, v in CRIT_ORDER.items()}


def _tier_key(k):
    """A `crit_by_tier` key coerced to an int tier, or None if it isn't an integer tier (bool is ambiguous
    and ignored; a float like 2.0 is accepted; a nested/other type is ignored, never crashes)."""
    if isinstance(k, bool):
        return None
    if isinstance(k, int):
        return k
    if isinstance(k, float) and k.is_integer():
        return int(k)
    if isinstance(k, str) and k.lstrip("-").isdigit():
        return int(k)
    return None


def resolve_crit(step_meta, tier):
    """Effective criticality of a catalog step at a tier. Criticality may only RISE with tier, so the
    result is the MAX (by severity) of `crit` and every valid `crit_by_tier` value whose key <= tier — a
    non-monotonic catalog can never LOWER a floor at runtime (round-2 defense-in-depth). Tolerant of a
    malformed cbt (non-dict, exotic keys, or a non-string value) — it is ignored, never crashed (round-3)."""
    if not isinstance(step_meta, dict):
        return "standard"
    base = step_meta.get("crit", "standard")
    if not isinstance(base, str) or base not in CRIT_ORDER:   # a non-string crit (e.g. [floor]) is unhashable (round-4 LOW-1)
        base = "standard"
    best = CRIT_ORDER[base]
    cbt = step_meta.get("crit_by_tier")
    if isinstance(cbt, dict):
        for k, v in cbt.items():
            tk = _tier_key(k)
            if tk is not None and tk <= tier and isinstance(v, str) and v in CRIT_ORDER:
                best = max(best, CRIT_ORDER[v])
    return _CRIT_BY_RANK[best]


def load_catalog(workflows_path, workflow_id="development"):
    """{ step_key: {crit, crit_by_tier, no_omit} } for one workflow. An unknown/typo'd workflow id returns
    an EMPTY catalog (so every skip resolves to UNKNOWN_STEP — fail closed) rather than a KeyError (round-3)."""
    import yaml
    d = yaml.safe_load(open(workflows_path))
    wfs = d.get("workflows", {}) if isinstance(d, dict) else {}
    wf = wfs.get(workflow_id) if isinstance(wfs, dict) else None
    steps = wf.get("steps") if isinstance(wf, dict) else None
    return {s["key"]: s for s in (steps or []) if isinstance(s, dict) and isinstance(s.get("key"), str)}


def lint_catalog(catalog):
    """CRIT_MONOTONIC — criticality may only rise with tier, never fall (LLD §11 / NEG-8)."""
    findings = []
    for key, meta in (catalog.items() if isinstance(catalog, dict) else []):
        if not isinstance(meta, dict):
            continue
        base = meta.get("crit", "standard")
        b = CRIT_ORDER.get(base, 1) if isinstance(base, str) else 1   # non-string crit is unhashable (round-4 LOW-1)
        cbt = meta.get("crit_by_tier")
        pairs = [(_tier_key(k), v) for k, v in cbt.items()] if isinstance(cbt, dict) else []
        ordered = sorted(((tk, v) for tk, v in pairs if tk is not None and isinstance(v, str)), key=lambda x: x[0])
        prev = b
        for tier, v in ordered:
            cur = CRIT_ORDER.get(v, 1)
            if cur < b or cur < prev:
                findings.append(_f("CRIT_MONOTONIC", f"step '{key}': crit_by_tier lowers criticality at tier {tier} ('{v}' < base/prev)"))
            prev = cur
    return findings


def _f(code, msg):
    return {"code": code, "message": msg, "waivable": code not in NON_WAIVABLE}


def check(change, catalog, tier=None, rollup=None, change_dir="."):
    """Validate a change record's skip ledger. Returns a list of findings (empty = clean)."""
    findings = []
    if not isinstance(change, dict):
        return [_f("SILENT_SKIP", "change record is not a mapping")]
    if not change.get("first_pass"):
        return findings  # not a First Pass change — nothing to enforce (back-compat)

    # tier must be a real int in range — a string "3" or bool True must NOT silently default to 2 and let
    # a tier-3 floor escape (round-1 HIGH-3). Fail closed AND evaluate at the strictest tier so no floor hides.
    tier = change.get("tier") if tier is None else tier
    if type(tier) is not int or not (0 <= tier <= 4):
        findings.append(_f("INVALID_TIER", f"tier {tier!r} is not an integer in 0..4"))
        tier = 4   # fail-safe: resolve criticality at the most restrictive tier

    # a structure that is PRESENT but not the expected type must NOT be coerced to empty — that hides a
    # skipped floor step in a `steps`/`skips` mapping (round-2 MED). Fail closed, non-waivable.
    wf = change.get("workflow")
    wf = wf if isinstance(wf, dict) else {}
    raw_steps, raw_skips = wf.get("steps"), change.get("skips")
    if raw_steps is not None and not isinstance(raw_steps, list):
        findings.append(_f("MALFORMED", f"workflow.steps is present but not a list ({type(raw_steps).__name__})"))
    if raw_skips is not None and not isinstance(raw_skips, list):
        findings.append(_f("MALFORMED", f"skips is present but not a list ({type(raw_skips).__name__})"))
    if change.get("workflow") is not None and not isinstance(change.get("workflow"), dict):
        findings.append(_f("MALFORMED", "workflow is present but not a mapping"))

    # a non-dict step entry, or a dict step whose `key` is missing/not a string, is malformed (round-3):
    # flag it and keep it OUT of the step map (a non-string key would also be unhashable → crash).
    steps, seen_keys = {}, {}
    for s in _list(raw_steps):
        if not isinstance(s, dict):
            findings.append(_f("MALFORMED", f"step entry is not a mapping: {s!r}"))
            continue
        k = s.get("key")
        if not isinstance(k, str):
            findings.append(_f("MALFORMED", f"step entry has a missing/non-string key: {k!r}"))
            continue
        seen_keys[k] = seen_keys.get(k, 0) + 1   # a duplicate key can mask a skip behind a later `done` (round-2)
        steps[k] = s
    for k, n in seen_keys.items():
        if n > 1:
            findings.append(_f("MALFORMED", f"duplicate step key '{k}' ({n}x) — statuses may mask each other"))
    skips = [s for s in _list(raw_skips) if isinstance(s, dict)]
    skip_by_step = {}
    for s in skips:
        skip_by_step.setdefault(_str(s.get("step")), []).append(s)

    # 0) every step status must be recognized — an unknown status (e.g. "declined") is a fail-open vector
    #    that hides a lightened floor step with no record (round-1 CRIT-2). Non-waivable.
    for key, st in steps.items():
        status = st.get("status")
        if status is not None and (not isinstance(status, str) or status not in VALID_STATUSES):
            findings.append(_f("INVALID_STATUS", f"step '{key}' has unrecognized status {status!r} (expected {sorted(VALID_STATUSES)})"))

    # 1) LEDGER_STEPS both ways (NEG-7): every skipped/starter step has a record; every record maps to such a step.
    for key, st in steps.items():
        status = st.get("status")   # a non-string status is unhashable → guard the set membership (round-4 LOW-2)
        if isinstance(status, str) and status in LIGHTENED_STATUSES and not skip_by_step.get(key):
            findings.append(_f("SILENT_SKIP", f"step '{key}' is {st.get('status')} but has no skip record"))
    for s in skips:
        k = _str(s.get("step"))
        if k not in steps:
            findings.append(_f("LEDGER_STEPS", f"skip record references unknown step '{k}'"))
        elif steps[k].get("status") not in ("skipped", "starter"):
            findings.append(_f("LEDGER_STEPS", f"skip record for '{k}' but step status is '{steps[k].get('status')}'"))

    # 2) per-record checks
    for s in skips:
        key = _str(s.get("step"))
        # never silent (NEG-1/2): actor + reason non-empty, valid disposition
        if not _str(s.get("actor")).strip():
            findings.append(_f("SILENT_SKIP", f"skip '{key}': actor is empty"))
        if not _str(s.get("reason")).strip():
            findings.append(_f("SILENT_SKIP", f"skip '{key}': reason is empty"))
        disp = _str(s.get("disposition"))
        if disp not in DISPOSITIONS:
            findings.append(_f("SILENT_SKIP", f"skip '{key}': disposition '{disp}' invalid (expected {sorted(DISPOSITIONS)})"))

        # a skip whose step key is not in the catalog can't have its criticality resolved — it must NOT
        # degrade to `standard` and slip a floor step past (round-1 CRIT-1: "deploy " / "Deploy" / typos).
        if key not in catalog:
            findings.append(_f("UNKNOWN_STEP", f"skip references step '{key}' not in the workflow catalog (criticality unresolvable)"))
            continue
        meta = catalog[key]
        crit = resolve_crit(meta, tier)
        no_omit = bool(meta.get("no_omit"))

        # NO_OMIT (NEG-5): a no_omit step may be starter, never defer/decline
        if no_omit and disp in ("defer", "decline"):
            findings.append(_f("NO_OMIT", f"step '{key}' is no_omit (starter-only) — cannot be {disp}"))

        # floor authority (NEG-3): floor skip needs ack_by
        if crit == "floor":
            if not _str(s.get("ack_by")).strip():
                findings.append(_f("FLOOR_NO_ACK", f"floor step '{key}' skipped with no ack_by (accountable role)"))
            # floor + hard gate needs a linked waiver (NEG-4)
            if key in HARD_GATE_STEPS and not _str(s.get("waiver_ref")).strip():
                findings.append(_f("FLOOR_NO_WAIVER", f"floor step '{key}' maps to a hard gate but has no waiver_ref (skip != waiver)"))

        # starter quality (NEG-6): artifact set + marked needs-enhancement
        if disp == "starter":
            art = _str(s.get("starter_artifact")).strip()
            if not art:
                findings.append(_f("STARTER_MARK", f"starter '{key}': no starter_artifact path"))
            else:
                path = art if os.path.isabs(art) else os.path.join(change_dir, art)
                # isfile (not exists) — a directory/symlink-to-dir must FAIL CLOSED, not crash open() (round-2 HIGH)
                if not os.path.isfile(path):
                    findings.append(_f("STARTER_MARK", f"starter '{key}': artifact '{art}' is not a readable file"))
                else:
                    try:
                        content = open(path, errors="ignore").read()
                    except OSError as e:
                        findings.append(_f("STARTER_MARK", f"starter '{key}': cannot read artifact '{art}' ({e.__class__.__name__})"))
                        content = ""
                    # the marker must head its own line (a real annotation) — not be buried in a comment
                    # or unrelated prose (round-1 LOW: naive substring accepted `<!-- needs-enhancement -->`).
                    if not any(ln.lstrip().lower().startswith(STARTER_MARKER) for ln in content.splitlines()):
                        findings.append(_f("STARTER_MARK", f"starter '{key}': artifact '{art}' has no '{STARTER_MARKER}' line"))

        # defer seeds a follow-up (CR-7) — warn if missing (waivable)
        if disp == "defer" and not _str(s.get("followup_ref")).strip():
            findings.append(_f("DEFER_NO_FOLLOWUP", f"deferred '{key}': no followup_ref (fast-follow not linked)"))

    # 3) ROLLUP (NEG-9): every per-change skip present in the project roll-up
    if rollup is not None:
        if not isinstance(rollup, dict):
            # the roll-up is an AUXILIARY project file (resurfacing), not the change's ledger — a malformed
            # one WARNS (like a missing entry), it does not block the change (round-4 LOW-3, consistent leniency)
            findings.append(_f("ROLLUP", f"roll-up is present but not a mapping ({type(rollup).__name__}) — resurfacing degraded"))
            rollup = {}
        rolled = {(_str(e.get("change_id")), _str(e.get("step")))
                  for e in _list(rollup.get("entries")) if isinstance(e, dict)}
        cid = _str(change.get("change_id"))
        for s in skips:
            if (cid, _str(s.get("step"))) not in rolled:
                findings.append(_f("ROLLUP", f"skip '{_str(s.get('step'))}' not reflected in .hitl/skip-ledger.yaml roll-up"))

    return findings


def run(change_path, workflows_path, rollup_path=None, tier=None):
    """Load + validate. NEVER raises on hostile input — any residual exception becomes a MALFORMED
    blocker so the CLI honors its 'exit 2, never traceback' contract (round-3). A caller that treats only
    a clean result as safe therefore fails CLOSED."""
    import yaml
    try:
        change = _strict_load(change_path)   # rejects duplicate keys (round-4 LOW-4)
    except Exception as e:  # noqa: BLE001
        return [_f("MALFORMED", f"cannot parse change file: {e.__class__.__name__}")]
    if not isinstance(change, dict):
        return [_f("MALFORMED", "change record is not a mapping")]
    # resolve the workflow id defensively — a string/typo/non-str yields an empty catalog (fail closed)
    wf = change.get("workflow")
    wid = wf.get("id") if isinstance(wf, dict) else None
    wid = wid if isinstance(wid, str) else "development"
    try:
        catalog = load_catalog(workflows_path, wid)
    except Exception:  # noqa: BLE001
        catalog = {}
    rollup = None
    if rollup_path and os.path.exists(rollup_path):
        try:
            rollup = yaml.safe_load(open(rollup_path))
        except Exception:  # noqa: BLE001
            rollup = {"entries": []}
    try:
        return lint_catalog(catalog) + check(change, catalog, tier=tier, rollup=rollup,
                                             change_dir=os.path.dirname(os.path.abspath(change_path)))
    except Exception as e:  # noqa: BLE001 — fail CLOSED, never traceback
        return [_f("MALFORMED", f"validation crashed on malformed input: {e.__class__.__name__}: {e}")]


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="First Pass skip-ledger validator (fail-closed)")
    ap.add_argument("change", help="path to .hitl/current-change.yaml")
    ap.add_argument("--workflows", default="ai/shared/workflows.yaml")
    ap.add_argument("--rollup", default=None, help="path to .hitl/skip-ledger.yaml")
    ap.add_argument("--tier", type=int, default=None)
    a = ap.parse_args()
    fs = run(a.change, a.workflows, a.rollup, a.tier)
    blockers = [f for f in fs if not f["waivable"]]
    for f in fs:
        tag = "BLOCK" if not f["waivable"] else "warn"
        print(f"[{tag}] {f['code']}: {f['message']}")
    if not fs:
        print("First Pass skip ledger: clean.")
    sys.exit(2 if blockers else 0)
