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

CRIT_ORDER = {"ceremony": 0, "standard": 1, "floor": 2}
DISPOSITIONS = {"defer", "decline", "starter"}
# Floor steps whose skip also needs a linked waiver because they map to a fail-closed / PR-blocking gate.
HARD_GATE_STEPS = {"conventions", "security_review", "qa_verify", "arch_review", "manifest_validate"}
# Non-waivable finding codes — the framework's guarantee under First Pass.
NON_WAIVABLE = {"SILENT_SKIP", "FLOOR_NO_ACK", "FLOOR_NO_WAIVER", "NO_OMIT"}
STARTER_MARKER = "needs-enhancement"


def _list(x):   return x if isinstance(x, list) else []
def _str(v):    return v if isinstance(v, str) else ""


def resolve_crit(step_meta, tier):
    """Effective criticality of a catalog step at a tier: the highest `crit_by_tier` key <= tier, else `crit`."""
    base = step_meta.get("crit", "standard")
    if base not in CRIT_ORDER:
        base = "standard"
    cbt = step_meta.get("crit_by_tier") or {}
    keys = [int(k) for k in cbt if str(k).lstrip("-").isdigit() and int(k) <= tier]
    if keys:
        v = cbt[max(keys)] if max(keys) in cbt else cbt[str(max(keys))]
        return v if v in CRIT_ORDER else base
    return base


def load_catalog(workflows_path, workflow_id="development"):
    """{ step_key: {crit, crit_by_tier, no_omit} } for one workflow in ai/shared/workflows.yaml."""
    import yaml
    d = yaml.safe_load(open(workflows_path))
    steps = d["workflows"][workflow_id]["steps"]
    return {s["key"]: s for s in steps if isinstance(s, dict) and "key" in s}


def lint_catalog(catalog):
    """CRIT_MONOTONIC — criticality may only rise with tier, never fall (LLD §11 / NEG-8)."""
    findings = []
    for key, meta in catalog.items():
        base = meta.get("crit", "standard")
        b = CRIT_ORDER.get(base, 1)
        cbt = meta.get("crit_by_tier") or {}
        ordered = sorted(((int(k), v) for k, v in cbt.items() if str(k).lstrip("-").isdigit()), key=lambda x: x[0])
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

    tier = change.get("tier") if tier is None else tier
    tier = tier if isinstance(tier, int) else 2
    steps = {s.get("key"): s for s in _list(change.get("workflow", {}).get("steps")) if isinstance(s, dict)}
    skips = [s for s in _list(change.get("skips")) if isinstance(s, dict)]
    skip_by_step = {}
    for s in skips:
        skip_by_step.setdefault(_str(s.get("step")), []).append(s)

    # 1) LEDGER_STEPS both ways (NEG-7): every skipped/starter step has a record; every record maps to such a step.
    for key, st in steps.items():
        if st.get("status") in ("skipped", "starter") and not skip_by_step.get(key):
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

        meta = catalog.get(key, {})
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
                if not os.path.exists(path):
                    findings.append(_f("STARTER_MARK", f"starter '{key}': artifact '{art}' does not exist"))
                elif STARTER_MARKER not in open(path, errors="ignore").read():
                    findings.append(_f("STARTER_MARK", f"starter '{key}': artifact '{art}' is not marked '{STARTER_MARKER}'"))

        # defer seeds a follow-up (CR-7) — warn if missing (waivable)
        if disp == "defer" and not _str(s.get("followup_ref")).strip():
            findings.append(_f("DEFER_NO_FOLLOWUP", f"deferred '{key}': no followup_ref (fast-follow not linked)"))

    # 3) ROLLUP (NEG-9): every per-change skip present in the project roll-up
    if rollup is not None:
        rolled = {(_str(e.get("change_id")), _str(e.get("step")))
                  for e in _list(rollup.get("entries")) if isinstance(e, dict)}
        cid = _str(change.get("change_id"))
        for s in skips:
            if (cid, _str(s.get("step"))) not in rolled:
                findings.append(_f("ROLLUP", f"skip '{_str(s.get('step'))}' not reflected in .hitl/skip-ledger.yaml roll-up"))

    return findings


def run(change_path, workflows_path, rollup_path=None, tier=None):
    import yaml
    change = yaml.safe_load(open(change_path))
    catalog = load_catalog(workflows_path, (change or {}).get("workflow", {}).get("id", "development"))
    rollup = yaml.safe_load(open(rollup_path)) if rollup_path and os.path.exists(rollup_path) else None
    findings = lint_catalog(catalog) + check(change, catalog, tier=tier, rollup=rollup,
                                             change_dir=os.path.dirname(os.path.abspath(change_path)))
    return findings


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
