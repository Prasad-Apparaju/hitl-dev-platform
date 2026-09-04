#!/usr/bin/env python3
"""Turn impact-analysis findings into a plan (#97).

This is the piece both skills call. `apply-change` runs it to record what the rules concluded;
`start-change` runs it to build the plan and pre-select the First Pass menu. Keeping it in one
place is the point: two implementations of "which steps does this change need" would disagree,
and the disagreement would be invisible.

TWO PREDICATES, NOT ONE.

    engages     does this step make sense for this change at all?   -> full scale
    needed_now  must it happen before this ships?                   -> fast track

An earlier draft used one field for both, so the two options resolved to the same list and the
choice offered nothing. They are separate fields in the catalog and separate answers here.

WHAT THE RULES MAY READ.

Only the finding fields defined in `ai/shared/templates/impact-record.schema.yaml`, which describe
what THIS CHANGE touches. Never what its area happens to have. A rule keyed to an area's paperwork
answers the same for every change to it, so a one-line fix in the best-documented code would draw
the longest plan and documenting an area would tax every future change to it.

The old predicates matched folder names and profiles. Profiles never reached the runtime, so five
steps could never fire at all; folder names are guesswork about what a path means.
"""
import sys

# Rules the catalog may express. Deliberately small: anything more expressive becomes a language
# nobody can read at the moment they are deciding whether to trust its answer.
_FORMS = ("any", "all")


def truth(pred, findings):
    """One predicate against the findings.

    A list field is true when non-empty; a boolean is itself. `surfaces:ui` asks membership.
    A field the findings do not carry is FALSE, not an error: an analysis that could not answer a
    question has not established the fact the rule needs, and a rule firing on an unanswered
    question is worse than one that does not fire.
    """
    if pred.startswith("surfaces:"):
        want = pred.split(":", 1)[1]
        return want in (findings.get("surfaces") or [])
    return bool(findings.get(pred))


def evaluate(rule, findings):
    """A whole rule. `always` / `never`, or a single {any|all: [...]}."""
    if rule == "always":
        return True
    if rule == "never":
        return False
    if not isinstance(rule, dict) or len(rule) != 1:
        raise ValueError("rule must be always/never or a single {any|all: [...]}, got %r" % (rule,))
    form, preds = next(iter(rule.items()))
    if form not in _FORMS:
        raise ValueError("unknown rule form %r (expected one of %s)" % (form, list(_FORMS)))
    if not preds:
        raise ValueError("empty predicate list is never true; say `never`")
    fn = any if form == "any" else all
    return fn(truth(p, findings) for p in preds)


def why(rule, findings):
    """The sentence shown next to a step, naming the finding that decided it.

    A person deciding whether to untick something needs the fact, not the rule. "three areas depend
    on this" is actionable; "engages: {any: [dependents]}" is not.
    """
    if rule == "always":
        return "applies to every change"
    if rule == "never":
        # Read by a person deciding whether to put it back, so say what the rule means rather than
        # that a rule exists. These are the steps that are worth doing and never block shipping.
        return "not required before this ships"
    form, preds = next(iter(rule.items()))
    fired = [p for p in preds if truth(p, findings)]
    if not fired:
        return "no %s in this change" % " or ".join(p.replace("_", " ") for p in preds)
    bits = []
    for p in fired:
        v = findings.get(p.split(":", 1)[0] if p.startswith("surfaces:") else p)
        if p.startswith("surfaces:"):
            bits.append("touches %s" % p.split(":", 1)[1])
        elif isinstance(v, list):
            bits.append("%d %s" % (len(v), p.replace("_", " ")))
        else:
            bits.append(p.replace("_", " "))
    return ", ".join(bits)


def locked_keys(catalog, tier, resolve_crit):
    """Steps a rule may never drop: the tier floor, the test-first cycle, and the retrospective.

    `locked` is not "impossible". check_skips allows a floor skip as a risk-accepted decision with
    an accountable person's ack_by. What locked means here is that the RULES cannot retire it —
    RULE_OVER_FLOOR blocks `not_applicable` on any of these. A floor step is dropped by a named
    human or not at all.
    """
    out = set()
    for key, meta in catalog.items():
        if not isinstance(meta, dict):
            continue
        if resolve_crit(meta, tier) == "floor" or meta.get("no_omit"):
            out.add(key)
    return out


def size(findings, catalog, costs, tier, resolve_crit):
    """Every step's verdict, in catalog order.

    Returns a list of dicts matching `rule_outcomes` in impact-record.schema.yaml, so the caller
    writes the record without reshaping. `judged` is always False here: this function only reports
    what a rule said. Where no rule fits, HITL decides and sets it when writing the record, which
    keeps overrides countable and separable from what the rules did on their own.
    """
    locked = locked_keys(catalog, tier, resolve_crit)
    out = []
    for key in catalog:
        entry = costs.get(key)
        if not entry:
            # A step with no rules cannot be sized. Failing closed (treating it as needed) is right:
            # the alternative silently drops a step nobody wrote a rule for.
            out.append({"step": key, "applies": True, "needed_now": True,
                        "because": "no rules declared for this step",
                        "because_applies": "no rules declared for this step",
                        "because_needed": "no rules declared for this step",
                        "judged": False, "locked": key in locked})
            continue
        applies = evaluate(entry.get("engages", "always"), findings)
        needed = evaluate(entry.get("needed_now", "always"), findings)
        meta = catalog.get(key) if isinstance(catalog.get(key), dict) else {}
        cond = meta.get("cond")
        # BOTH sentences are kept, because the reason a step is in is not the reason it is out.
        # A single `because` field returned the `engages` sentence whenever `needed_now` was false,
        # so every fast-track exclusion carried an affirmative finding: `packet` was dropped with
        # the reason "applies to every change", and that string is what a person confirms, what
        # reaches the roll-up, and what the retrospective reads back as what was left out and why.
        why_applies = why(entry.get("engages", "always"), findings)
        why_needed = why(entry.get("needed_now", "always"), findings)
        is_locked = key in locked
        if cond and not applies:
            # A conditional step is in the plan only when its activator fires (#102). The floor says
            # how an ACTIVE step may be skipped; it does not conjure the step into changes it is not
            # about — otherwise `pentest` (floor) would lock into every typo fix. Inactive, it is
            # not locked, and it is excluded with the reason its activator did not fire.
            needed = False
            is_locked = False
            reason = why_applies = why_needed = "conditional (%s) not activated: %s" % (cond, why_applies)
        elif is_locked:
            # The floor is not up for rule-based removal. Say so in the same field, so the reason
            # shown to a person is the real one rather than whichever predicate happened to fire.
            applies = needed = True
            reason = why_applies = why_needed = "locked at tier %s" % tier
        else:
            reason = why_needed if needed else why_applies
        out.append({"step": key, "applies": applies, "needed_now": needed,
                    "because": reason, "because_applies": why_applies, "because_needed": why_needed,
                    "judged": False, "locked": is_locked})
    return out


def plan(outcomes, option):
    """The step keys for an option. `full` is what applies; `fast` is what is needed now."""
    if option not in ("fast", "full"):
        raise ValueError("option must be 'fast' or 'full', got %r" % (option,))
    field = "needed_now" if option == "fast" else "applies"
    return [o["step"] for o in outcomes if o[field]]


def excluded(outcomes, option):
    """What the option leaves out, with the reason each was left out.

    These become `not_applicable` ledger entries, carrying the rule that decided them. They are not
    a person declining work; without a disposition for that distinction the ledger records a human
    declining steps they never looked at.
    """
    field = "needed_now" if option == "fast" else "applies"
    # The reason must say why it is OUT, not why it applies. A step excluded from the fast track
    # was excluded by `needed_now`; a step excluded from full scale was excluded by `engages`.
    reason_field = "because_needed" if option == "fast" else "because_applies"
    return [{"step": o["step"], "reason": o.get(reason_field) or o["because"]}
            for o in outcomes if not o[field] and not o["locked"]]


def main(argv):
    """Size a plan from a written impact record. Prints the two options and what each leaves out.

    The TIER IS REQUIRED and is not read from the record. The record is written by the impact
    analysis, which is explicitly not allowed to set a tier — two writers for that field is how a
    tier set in one place disagrees with one set in another. Intake confirms the tier with a human
    at Step 4 and passes it here.

    It used to default to 3 when absent, and since a schema-conformant record never carries one,
    every change was sized at the strictest tier: a one-line fix with no dependents got `packet`,
    `arch_review`, `qa_verify`, `rollout` and `integration_verify` locked. That is precisely the
    over-ceremony this exists to remove, arriving silently. Defaulting was the bug; refusing is the
    fix.
    """
    import json
    import os
    import yaml
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from check_skips import load_catalog, resolve_crit

    # `workflows.yaml` is optional and resolved the same way everywhere else. The skill used to pass
    # a `$WFYAML` variable that was never assigned anywhere in the repo, so the command it printed
    # ran as `size_plan.py rec.yaml "" 2 fast` and died with FileNotFoundError on an empty path.
    from check_skips import default_workflows
    args = [a for a in argv[1:]]
    if len(args) >= 2 and (args[1].endswith(".yaml") or args[1].endswith(".yml")) \
            and not args[1].strip().isdigit():
        rec_path, wf_path, rest = args[0], args[1], args[2:]
    else:
        rec_path, wf_path, rest = args[0] if args else "", default_workflows(), args[1:]

    if not rec_path or not rest:
        print("usage: size_plan.py <impact-record.yaml> [workflows.yaml] <tier> [fast|full]",
              file=sys.stderr)
        return 2
    rec = yaml.safe_load(open(rec_path))
    wf = yaml.safe_load(open(wf_path))
    try:
        tier = int(rest[0])
    except ValueError:
        print("tier must be an integer 0-4, got %r" % rest[0], file=sys.stderr)
        return 2
    if not 0 <= tier <= 4:
        print("tier must be 0-4, got %d" % tier, file=sys.stderr)
        return 2
    if rec.get("tier") is not None and int(rec["tier"]) != tier:
        print("the record carries tier %r but %d was passed — the impact analysis must not set a "
              "tier, and two sources for it will disagree" % (rec["tier"], tier), file=sys.stderr)
        return 2

    # Size against the workflow the record was written for, not always `development`.
    # `load_catalog` defaults to development, so handing it a brownfield record used to return a
    # development plan with no warning and exit 0.
    workflow = rec.get("workflow") or "development"
    known = set((wf.get("workflows") or {}))
    if workflow not in known:
        print("record names workflow %r; the catalog defines %s" % (workflow, sorted(known)),
              file=sys.stderr)
        return 2
    catalog = load_catalog(wf_path, workflow)
    costs = wf.get("step_costs") or {}
    findings = rec.get("findings") or {}
    option = rest[1] if len(rest) > 1 else "fast"

    outcomes = size(findings, catalog, costs, tier, resolve_crit)

    # `step_costs` covers the development spine only. Sizing another workflow returns every step
    # with "no rules declared", so fast and full come out BYTE-IDENTICAL and the caller offers a
    # choice between two copies of the same list. Failing closed is right; doing it silently is not.
    unruled = [o["step"] for o in outcomes if o["because"] == "no rules declared for this step"]
    if unruled and len(unruled) == len(outcomes):
        print("workflow %r has no sizing rules for any of its %d steps, so both options are the "
              "whole plan. Do not offer a choice here." % (workflow, len(outcomes)), file=sys.stderr)
    elif unruled:
        print("%d of %d steps in %r have no sizing rules and are kept: %s"
              % (len(unruled), len(outcomes), workflow, ", ".join(unruled)), file=sys.stderr)

    print(json.dumps({"workflow": workflow, "tier": tier, "option": option,
                      "unruled": unruled,
                      "plan": plan(outcomes, option),
                      "excluded": excluded(outcomes, option),
                      "outcomes": outcomes}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
