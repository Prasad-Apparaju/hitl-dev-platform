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
                "UNKNOWN_STEP", "INVALID_STATUS", "INVALID_TIER", "MALFORMED", "CRIT_MONOTONIC",
                # a load-bearing step DELETED from the plan (not skipped, no record) is a bypass (codex-1)
                "INCOMPLETE_PLAN",
                # steps lightened while `first_pass` is absent: enforcement never engaged, so every other
                # check below was skipped and the ledger is uncertified. The bug this catches shipped
                # because the driver never emitted the flag.
                "FP_UNDECLARED",
                # an unmarked starter presented as complete is the "fabricated full artifact" ADR-6 forbids (codex-4)
                "STARTER_MARK"}
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


ACTOR_FIELDS = ("actor", "ack_by", "accepted_by", "authorized_by", "acknowledged_by")


def _actor_of(entry):
    """Who owns this skip. One dialect: check_review, skip-record.md and this file all accept these."""
    if not isinstance(entry, dict):
        return ""
    for f in ACTOR_FIELDS:
        v = _str(entry.get(f)).strip()
        if v:
            return v
    return ""


def _f(code, msg):
    return {"code": code, "message": msg, "waivable": code not in NON_WAIVABLE}


def check(change, catalog, tier=None, rollup=None, change_dir="."):
    """Validate a change record's skip ledger. Returns a list of findings (empty = clean)."""
    findings = []
    if not isinstance(change, dict):
        return [_f("SILENT_SKIP", "change record is not a mapping")]
    # `first_pass` gates enforcement, so its type is load-bearing: a falsey non-bool ([], {}, 0, "") must NOT
    # be read as an intentional `false` and disable the whole guarantee (codex-2). Enforce unless it is the
    # literal boolean False or genuinely absent; a present-but-non-bool value is MALFORMED *and* enforced.
    fp = change.get("first_pass")
    if fp is None or fp is False:
        # Back-compat still holds for a genuinely untouched plan, but "no flag" must not become the way
        # to lighten steps unchecked: every check below is gated on this early return, so an undeclared
        # change with skips in it certifies clean while enforcing nothing. `skipped`/`starter` statuses
        # post-date FR-29 and only the First Pass driver writes them, so their presence here means the
        # flag was lost or omitted, not that the file is legacy.
        # An entry carrying an accountable name is a decision someone owns. That is the record we
        # want to exist; refusing it teaches people not to write it.
        def _attributed(e):
            if not isinstance(e, dict):
                return False
            return bool(_actor_of(e))

        raw_skips = change.get("skips") if isinstance(change.get("skips"), list) else []
        unattributed = [e for e in raw_skips if not _attributed(e)]

        evidence = []
        if unattributed:
            evidence.append(f"{len(unattributed)} unattributed entr"
                            f"{'y' if len(unattributed) == 1 else 'ies'} in skips[]")
        wf = change.get("workflow")
        lightened = [
            s.get("key")
            for s in (wf.get("steps") if isinstance(wf, dict) and isinstance(wf.get("steps"), list) else [])
            # a non-string status is unhashable, and `x in set()` RAISES on those — guard the membership
            # the same way every other test in this file does (round-4 LOW-2). Without this, a legacy
            # file with `status: [done]` turns check() from "returns findings" into "throws".
            if isinstance(s, dict) and isinstance(s.get("status"), str) and s["status"] in LIGHTENED_STATUSES
        ]
        accounted = {_str(e.get("step")).strip() for e in raw_skips if _attributed(e)}
        lightened = [k for k in lightened if k not in accounted]
        if lightened:
            evidence.append("step(s) " + ", ".join(repr(k) for k in lightened[:5] if k)
                            + (" and more" if len(lightened) > 5 else "") + " lightened")
        if evidence:
            findings.append(_f(
                "FP_UNDECLARED",
                "first_pass is absent/false and the change has been lightened with nothing "
                "accountable behind it (" + "; ".join(evidence)
                + "). Give each skip an owner (`ack_by:` or `actor:`) and a reason, or restore the "
                  "steps. Do NOT set `first_pass: true` to clear this unless the change really is "
                  "running First Pass — that records something untrue to silence a check."))
        # Accepting an attributed skip must NOT mean skipping enforcement on it. Returning here
        # would let a floor step be declined with a name and no waiver, checked by nothing — worse
        # than the red PR this fix removes. So: legacy files with no skips still return (back-compat),
        # but a change carrying attributed skips falls through to the full ruleset below.
        if not any(_attributed(e) for e in raw_skips):
            return findings  # genuinely not a First Pass change — nothing further to enforce
    if fp is None:
        # Reached only via the attributed-skip fall-through above: the flag is legitimately absent
        # and we are enforcing anyway. Saying "present but not a boolean" would be untrue.
        findings.append(_f("FP_ABSENT_ENFORCED",
                           "first_pass is absent, but this change carries attributed skips — "
                           "enforcing the full ruleset on them."))
    elif type(fp) is not bool:
        findings.append(_f("MALFORMED", f"first_pass is present but not a boolean ({fp!r}) — enforcing at strictest"))

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

    # 0) every step must carry a recognized string status — a missing/null status (codex-3) or an unknown
    #    one (e.g. "declined", round-1 CRIT-2) is a fail-open vector that leaves a floor step in the plan
    #    with no state and no record. Every present step must be explicit. Non-waivable.
    for key, st in steps.items():
        status = st.get("status")
        if not isinstance(status, str) or status not in VALID_STATUSES:
            findings.append(_f("INVALID_STATUS", f"step '{key}' has missing/unrecognized status {status!r} (expected {sorted(VALID_STATUSES)})"))

    # 0.4) TIER ACCOUNTABILITY. Tier is self-declared and nothing validates it against what the change
    #    actually touches. Note where the protection really moves: 3 -> 2 takes impact, packet,
    #    arch_review, qa_verify and rollout off `floor` in one step; 2 -> 1 only moves
    #    integration_verify. So the demotion that matters is NOT the boundary guarded here — tier 2 is
    #    the default and asks for nothing. This check is the accountability price of the tier 0/1
    #    batch-decline path, not a floor guard; do not let its presence imply the floor is covered.
    #    Waivable: a genuinely trivial change should not be blocked, only accounted for.
    if isinstance(tier, int) and tier <= 1:
        if not _str(change.get("tier_set_by")).strip():
            findings.append(_f("TIER_UNATTRIBUTED", f"tier {tier} is declared with no `tier_set_by` — a light path is a human's call, not the agent's"))
        if not _str(change.get("tier_reason")).strip():
            findings.append(_f("TIER_UNATTRIBUTED", f"tier {tier} is declared with no `tier_reason` — record why this change qualifies"))

    # 0.5) PLAN COMPLETENESS (codex-1): a load-bearing step DELETED from the plan entirely leaves no status
    #    and no record to inspect — silently omitting it. Every catalog step that is `floor` (at this tier) or
    #    `no_omit` MUST be present in steps[]; a missing one is a non-waivable INCOMPLETE_PLAN. (Ceremony/
    #    standard steps may be absent — they're freely skippable — but a floor/TDD step can't just vanish.)
    for ckey, cmeta in (catalog.items() if isinstance(catalog, dict) else []):
        if not isinstance(cmeta, dict):
            continue
        must_be_present = resolve_crit(cmeta, tier) == "floor" or bool(cmeta.get("no_omit"))
        if must_be_present and ckey not in steps:
            findings.append(_f("INCOMPLETE_PLAN", f"load-bearing step '{ckey}' is missing from the plan (floor/no_omit steps cannot be omitted)"))
        # CR-3 says a step cannot be skipped without producing a record, and CR-16 says the plan shows
        # the WHOLE journey with lightened steps visible. Deleting a ceremony/standard step satisfied
        # neither: no record, and invisible in the trail. "Freely skippable" is about who may decide,
        # not about whether the decision is written down — and deletion was strictly cheaper than the
        # honest path (no actor, no reason, no resurfacing), which inverted the incentive CR-3 creates.
        # Waivable: pruning can be legitimate, it just may not be silent.
        elif not must_be_present and ckey not in steps and not skip_by_step.get(ckey):
            findings.append(_f("PLAN_PRUNED", f"catalog step '{ckey}' is absent from the plan with no skip record — record it as a skip (CR-3), or waive if the step cannot apply to this change"))

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
        if not _actor_of(s):
            findings.append(_f("SILENT_SKIP",
                               f"skip '{key}': nobody is accountable for it — set `actor:` "
                               f"(or `ack_by:`) to a person or role"))
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
            # A starter is only meaningful where an honest-minimal version is DEFINED. The driver
            # refuses unregistered starters, but certification is the boundary that has to hold for
            # hand-authored and migrated records too — a menu is not an enforcement boundary.
            try:
                from starters import has_starter as _has_starter
            except Exception:
                _has_starter = None
            if _has_starter is not None and not _has_starter(key):
                findings.append(_f("STARTER_MARK", f"starter '{key}': no registered starter exists for this step — use defer or decline"))
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


def _default_workflows():
    """Locate the criticality catalog. In an onboarded product repo it is co-located with this validator
    (`ci/first-pass/workflows.yaml`); in the source platform repo it is `ai/shared/workflows.yaml`. Try
    both so the CLI needs no `--workflows` in either layout."""
    here = os.path.dirname(os.path.abspath(__file__))
    for cand in (os.path.join(here, "workflows.yaml"),
                 os.path.join(here, "..", "..", "ai", "shared", "workflows.yaml")):
        if os.path.exists(cand):
            return cand
    return "ai/shared/workflows.yaml"


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="First Pass skip-ledger validator (fail-closed)")
    ap.add_argument("change", help="path to .hitl/current-change.yaml")
    ap.add_argument("--workflows", default=_default_workflows())
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
