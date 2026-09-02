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
        return "never required by a rule"
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
                        "because": "no rules declared for this step", "judged": False,
                        "locked": key in locked})
            continue
        applies = evaluate(entry.get("engages", "always"), findings)
        needed = evaluate(entry.get("needed_now", "always"), findings)
        if key in locked:
            # The floor is not up for rule-based removal. Say so in the same field, so the reason
            # shown to a person is the real one rather than whichever predicate happened to fire.
            applies = needed = True
            reason = "locked at tier %s" % tier
        else:
            reason = why(entry.get("needed_now", "always"), findings) if needed \
                else why(entry.get("engages", "always"), findings)
        out.append({"step": key, "applies": applies, "needed_now": needed,
                    "because": reason, "judged": False, "locked": key in locked})
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
    return [{"step": o["step"], "reason": o["because"]}
            for o in outcomes if not o[field] and not o["locked"]]


def main(argv):
    """Size a plan from a written impact record. Prints the two options and what each leaves out."""
    import json
    import os
    import yaml
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from check_skips import load_catalog, resolve_crit

    if len(argv) < 3:
        print("usage: size_plan.py <impact-record.yaml> <workflows.yaml> [fast|full]", file=sys.stderr)
        return 2
    rec = yaml.safe_load(open(argv[1]))
    wf = yaml.safe_load(open(argv[2]))
    catalog = load_catalog(argv[2])
    costs = wf.get("step_costs") or {}
    findings = rec.get("findings") or {}
    tier = rec.get("tier", 3)
    option = argv[3] if len(argv) > 3 else "fast"

    outcomes = size(findings, catalog, costs, tier, resolve_crit)
    print(json.dumps({"option": option,
                      "plan": plan(outcomes, option),
                      "excluded": excluded(outcomes, option),
                      "outcomes": outcomes}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
