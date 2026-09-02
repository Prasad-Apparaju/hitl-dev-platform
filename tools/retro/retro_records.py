#!/usr/bin/env python3
"""Closing retrospective (#98) — records module.

The retrospective is a pure function of records that already exist when a change closes: the
change file, the impact record, and the review records. It collects nothing new, publishes
nothing, and asks nobody to approve anything. That is what makes floor-at-every-tier honest
(design: docs/design/progress-and-retro/01-design.md).

The load-bearing property is NO-EDIT. The retrospective records observations ABOUT the sizing
rules and never authors a rule field. A mechanism that judges its own sizing and then rewrites
the rules it was judged by is grading its own homework. This mirrors the Advisor's NO-AUTHOR
boundary (tools/agentic-advisor/records.py:211) and is enforced the same way, in
ci/retro/test_records.py — because a boundary nobody tests erodes on the first convenient
afternoon.

The observation channel is a PROJECTION, exactly like the Advisor's skip channel: what a rule
concluded is carried under `concluded_applies` / `concluded_needed_now`, never under the raw
`engages` / `needed_now` keys. So a retrospective can say what a rule decided without ever
holding a value that could be pasted back into the catalog.
"""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "ci", "first-pass"))

try:
    import yaml
except ImportError:                                          # pragma: no cover
    yaml = None

# The blameless voice is defined once, in the resurfacing lint, and reused here rather than
# redefined. A second copy is a second thing to drift (design: "reuses both rather than
# inventing a second tone nobody checks").
try:
    import resurface as _resurface
    _BLAME_RE = _resurface._BLAME_RE
    _clean = _resurface._clean
except Exception:                                            # pragma: no cover - lint unavailable
    _BLAME_RE = re.compile(r"(?!x)x")
    def _clean(text):
        return str(text)


# ── The boundary ──────────────────────────────────────────────────────────────────────────
# Rule-defining fields, derived from the runtime catalog so a newly added rule field widens the
# ban automatically. The static set is the floor, not the whole answer.
_STATIC_CATALOG_FIELDS = {
    "crit", "crit_by_tier", "command",           # what a step is and what runs it
    "engages", "needed_now", "forgo_cost",       # the sizing predicates
    "protects",                                  # the rationale the predicates carry
    "rules", "sizing_rules", "rule",
}

_HERE = os.path.dirname(os.path.abspath(__file__))
# The catalog sits at a different depth in the two layouts this module ships in. Source keeps it at
# ai/shared/workflows.yaml; the built plugin flattens it to shared/workflows.yaml, one level above
# shared/tools/retro/. Resolving only the first is how the derived ban set silently degrades to the
# static one in the shipped package, with nothing to say it happened.
_CATALOG_CANDIDATES = (
    os.path.normpath(os.path.join(_HERE, "..", "..", "ai", "shared", "workflows.yaml")),  # source
    os.path.normpath(os.path.join(_HERE, "..", "..", "workflows.yaml")),                  # plugin
)


def _resolve_catalog(candidates=_CATALOG_CANDIDATES):
    for c in candidates:
        if os.path.isfile(c):
            return c
    return None


def _catalog_field_names(path=None):
    """Every key that defines a sizing rule, read from the catalog itself where possible."""
    names = set(_STATIC_CATALOG_FIELDS)
    path = path or _resolve_catalog()
    if yaml is None or not path or not os.path.isfile(path):
        return names
    try:
        with open(path) as fh:
            doc = yaml.safe_load(fh) or {}
    except Exception:
        return names
    for entry in (doc.get("step_costs") or {}).values():
        if isinstance(entry, dict):
            names |= set(entry.keys())
    for wf in (doc.get("workflows") or {}).values():
        steps = wf.get("steps") if isinstance(wf, dict) else None
        for step in steps or []:
            if isinstance(step, dict):
                names |= {k for k in step if k not in ("key", "n", "label", "phase")}
    return names


CATALOG_FIELDS = _catalog_field_names()

# The projected observation channel. A retrospective carries exactly these about a rule.
OBSERVATION_FIELDS = ("step", "concluded_applies", "concluded_needed_now", "because",
                      "judged", "observed")


def retro_authors_no_catalog_field(retro):
    """NO-EDIT: the retrospective holds no workflow-catalog rule field value (no `crit`, no
    `engages`, …). Returns the set of offending keys found anywhere (empty ⇒ clean)."""
    found = set()

    def walk(x):
        if isinstance(x, dict):
            for k, v in x.items():
                if k in CATALOG_FIELDS:
                    found.add(k)
                walk(v)
        elif isinstance(x, list):
            for e in x:
                walk(e)

    walk(retro)
    return found


def blame_words_in(text):
    """Blame vocabulary present in `text`, using the resurfacing lint's own definition."""
    return {m.group(0).lower() for m in _BLAME_RE.finditer(str(text or ""))}


# ── Reading what already exists ───────────────────────────────────────────────────────────
def _str(x):
    return "" if x is None else str(x)


def _steps_of(change):
    wf = (change or {}).get("workflow") or {}
    return [s for s in (wf.get("steps") or []) if isinstance(s, dict)]


def _skips_of(change):
    raw = (change or {}).get("skips")
    return [s for s in raw if isinstance(s, dict)] if isinstance(raw, list) else []


def open_items(change):
    """What is still open at close: skipped steps, deferred work, and unverified criteria.

    This feeds the resurfacing that already exists, so the next change touching this area hears
    about it rather than the work disappearing at close."""
    items = []
    skip_by_step = {}
    for s in _skips_of(change):
        skip_by_step.setdefault(_str(s.get("step")).strip(), []).append(s)

    for step in _steps_of(change):
        key = _str(step.get("key")).strip()
        status = _str(step.get("status")).strip()
        if status not in ("skipped", "starter"):
            continue
        for record in skip_by_step.get(key, [{}]):
            items.append({
                "step": key,
                "label": _str(step.get("label")).strip(),
                "state": status,
                "disposition": _str(record.get("disposition")).strip(),
                "reason": _clean(_str(record.get("reason")).strip()),
                "owner": _str(record.get("ack_by") or record.get("actor")
                              or record.get("owner")).strip(),
            })

    for crit in (change or {}).get("acceptance_criteria") or []:
        if not isinstance(crit, dict):
            continue
        if not crit.get("verified"):
            items.append({
                "step": "",
                "label": _str(crit.get("id") or crit.get("criterion")).strip(),
                "state": "unverified",
                "disposition": "",
                "reason": _clean(_str(crit.get("note")).strip()),
                "owner": "",
            })
    return items


def sizing_observations(change, impact):
    """How the sizing turned out: what each rule concluded, against what actually happened.

    Returns projected observations (OBSERVATION_FIELDS). It never returns a rule field, so a
    caller cannot round-trip this into the catalog."""
    outcomes = (impact or {}).get("rule_outcomes")
    if not isinstance(outcomes, list):
        return []

    status_by_step = {}
    for step in _steps_of(change):
        status_by_step[_str(step.get("key")).strip()] = _str(step.get("status")).strip()

    observations = []
    for outcome in outcomes:
        if not isinstance(outcome, dict):
            continue
        key = _str(outcome.get("step")).strip()
        ran = status_by_step.get(key, "")
        concluded_needed = bool(outcome.get("needed_now"))
        if ran in ("skipped", "starter"):
            observed = "dropped from the plan"
        elif ran in ("done", "current", "open", ""):
            observed = "kept in the plan"
        else:
            observed = ran
        # The comparison the loop exists for, stated as an observation and nothing more.
        if concluded_needed and ran in ("skipped", "starter"):
            observed += " — the rule said it was needed now"
        elif not concluded_needed and ran == "done":
            observed += " — the rule said it was not needed now"
        observations.append({
            "step": key,
            "concluded_applies": bool(outcome.get("applies")),
            "concluded_needed_now": concluded_needed,
            "because": _clean(_str(outcome.get("because")).strip()),
            "judged": bool(outcome.get("judged")),
            "observed": observed,
        })
    return observations


def build_retro(change, impact=None, reviews=None):
    """The retrospective record: a pure function of records that already exist."""
    change = change or {}
    return {
        "change_id": _str(change.get("change_id") or change.get("id")).strip(),
        "tier": change.get("tier"),
        "what_happened": {
            "requirement": _str(change.get("requirement")).strip(),
            "issue": _str(((change.get("source_artifacts") or {}) or {}).get("issue")).strip(),
            "steps_planned": len(_steps_of(change)),
            "steps_dropped": sum(1 for s in _steps_of(change)
                                 if _str(s.get("status")).strip() in ("skipped", "starter")),
            "reviews": [_str(r).strip() for r in (reviews or [])],
        },
        "still_open": open_items(change),
        "sizing": sizing_observations(change, impact),
    }


def render(retro):
    """`.hitl/retro/<change_id>.md` — the local document, in the blameless voice."""
    retro = retro or {}
    happened = retro.get("what_happened") or {}
    lines = [f"# Closing retrospective — {retro.get('change_id') or '<change>'}", ""]

    lines += ["## What happened", ""]
    if happened.get("requirement"):
        lines += [f"Asked for: {happened['requirement']}", ""]
    if happened.get("issue"):
        lines += [f"Issue: {happened['issue']}", ""]
    lines += [f"The plan was {happened.get('steps_planned', 0)} steps; "
              f"{happened.get('steps_dropped', 0)} were left out.", ""]
    for record in happened.get("reviews") or []:
        lines.append(f"- review record: {record}")
    if happened.get("reviews"):
        lines.append("")

    lines += ["## What is still open", ""]
    items = retro.get("still_open") or []
    if not items:
        lines += ["Nothing was left out and every criterion was verified.", ""]
    for item in items:
        label = item.get("label") or item.get("step") or "?"
        bits = [f"- **{label}** — {item.get('state')}"]
        if item.get("disposition"):
            bits.append(f"({item['disposition']})")
        if item.get("reason"):
            bits.append(f": {item['reason']}")
        if item.get("owner"):
            bits.append(f" — recorded by {item['owner']}")
        lines.append(" ".join(bits))
    if items:
        lines.append("")

    lines += ["## How the sizing turned out", ""]
    observations = retro.get("sizing") or []
    if not observations:
        lines += ["The impact record carries no `rule_outcomes`, so there is nothing to compare "
                  "this change against.", ""]
    else:
        lines += ["| step | rule concluded | what happened | because |",
                  "|---|---|---|---|"]
        for obs in observations:
            concluded = "needed now" if obs.get("concluded_needed_now") else "not needed now"
            if obs.get("judged"):
                concluded += " (judged, no rule fit)"
            lines.append(f"| `{obs.get('step')}` | {concluded} | {obs.get('observed')} "
                         f"| {obs.get('because') or '—'} |")
        lines += ["", "These are observations. Changing a rule is a change, and goes through the "
                  "normal flow like any other.", ""]
    return "\n".join(lines).rstrip() + "\n"


if __name__ == "__main__":                                   # pragma: no cover
    import argparse
    ap = argparse.ArgumentParser(description="Write the closing retrospective for a change.")
    ap.add_argument("--change", default=".hitl/current-change.yaml")
    ap.add_argument("--impact", default="")
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    if yaml is None:
        sys.stderr.write("PyYAML is required\n")
        raise SystemExit(2)
    with open(args.change) as fh:
        change_doc = yaml.safe_load(fh) or {}
    impact_path = args.impact or _str(change_doc.get("impact_record")).strip()
    impact_doc = {}
    if impact_path and os.path.isfile(impact_path):
        with open(impact_path) as fh:
            impact_doc = yaml.safe_load(fh) or {}

    record = build_retro(change_doc, impact_doc)
    offending = retro_authors_no_catalog_field(record)
    if offending:
        sys.stderr.write("NO-EDIT violated: retrospective holds rule field(s) "
                         + ", ".join(sorted(offending)) + "\n")
        raise SystemExit(2)

    text = render(record)
    out = args.out or os.path.join(".hitl", "retro", f"{record['change_id']}.md")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as fh:
        fh.write(text)
    print(f"Retrospective written to {out}")
