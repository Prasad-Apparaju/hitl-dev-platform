#!/usr/bin/env python3
"""Turn a plan into the intake selection, and the selection into a choices file.

This is the CALLER. Three features of 2.9.0 were built, tested, shipped and invoked by nothing:
the ranker had no caller, the collapsed tail had no writer, and the shape probe set no variable.
Guards asserted their names appeared in a file, which is why the suite stayed green over all three.

Two entry points, both executable:

  render   read the plan + the change facts, print the selection a person reads
  choices  turn what they kept into .hitl/first-pass-choices.json — INCLUDING the tail, which is
           the whole compensation for the tail being skipped by default
"""
import argparse, json, os, sys, yaml

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.append(_HERE)   # append: the front of sys.path shadows the stdlib
import rank as R

OFFERED = 8                       # how many decidable steps are shown; the rest collapse


def source_paths(manifest):
    return [p for d in ((manifest or {}).get("domains") or []) if isinstance(d, dict)
            for p in (d.get("paths") or []) if isinstance(p, str)]




def build(plan, costs, requires, *, tier, paths, profile, tags, manifest, incidents):
    risky = R.risky_domains(manifest, incidents)
    ranked = R.rank_plan(plan, costs, tier=tier, paths=paths, profile=profile, tags=tags,
                         multi_domain=len(source_paths(manifest)) > 1,
                         risky_domain=R.touches_risky(paths, risky))
    locked = [r for r in ranked if r["locked"]]
    rest = [r for r in ranked if not r["locked"]]
    return locked, rest[:OFFERED], rest[OFFERED:]


def render(locked, offered, tail):
    out = []
    if locked:
        out.append("Running (locked)")
        for r in locked:
            out.append("   %-18s %s" % (r["key"], r["lock_reason"]))
        out.append("")
    out.append("Selected — untick any%swhat you'd lose" % (" " * 22))
    for r in offered:
        out.append("   [x] %-16s %-6s %s" % (r["key"], r["rank"], (r["protects"] or "")[:56]))
    if tail:
        out.append("")
        out.append("   + %d more, skipped and recorded: %s%s" %
                   (len(tail), ", ".join(t["key"] for t in tail[:6]),
                    " …" if len(tail) > 6 else ""))
    return "\n".join(out)


def choices(kept, offered, tail, requires, actor):
    """The choices file. Every step NOT kept gets an entry — offered or tail, no difference.

    The tail being 'skipped and recorded' is the compensation for it being skipped by default. If
    the tail never reaches this file it is skipped and NOT recorded, and the fail-closed validator
    certifies the change clean.
    """
    kept = set(kept or ())
    ch = {}
    for r in offered:
        if r["key"] not in kept:
            ch[r["key"]] = {"disposition": "decline",
                            "reason": "unticked at intake: %s" % (r["protects"] or "no reason given")}
    for r in tail:
        if r["key"] not in kept:
            ch[r["key"]] = {"disposition": "decline",
                            "reason": "below the cut line at intake (rank %s): %s"
                                      % (r["rank"], r["protects"] or "no reason given")}
    doc = {"actor": actor, "choices": ch}
    warn = R.incoherent(kept, requires)
    return doc, warn


def _load(path):
    try:
        with open(path) as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["render", "choices"])
    ap.add_argument("--workflows", default="ci/first-pass/workflows.yaml")
    ap.add_argument("--workflow", default="development")
    ap.add_argument("--tier", type=int, default=2)
    ap.add_argument("--profile", default="")
    ap.add_argument("--tags", default="")
    ap.add_argument("--paths", default="",
                    help="paths the change touches, from the impact analysis — NOT a git diff. "
                         "At intake there is no diff to read; impact analysis is the step that "
                         "knows this, by reading the code.")
    ap.add_argument("--manifest", default="docs/02-design/system-manifest.yaml")
    ap.add_argument("--incidents", default="docs/03-engineering/incident-registry.yaml")
    ap.add_argument("--keep", default="")
    ap.add_argument("--actor", default="")
    a = ap.parse_args(argv)

    wf = _load(a.workflows)
    manifest, incidents = _load(a.manifest), _load(a.incidents)
    paths = [p for p in a.paths.split(",") if p.strip()]

    block = (wf.get("workflows") or {}).get(a.workflow) or {}
    plan = block.get("steps") or []
    if not plan:
        print("no plan for workflow %r in %s" % (a.workflow, a.workflows), file=sys.stderr)
        return 2

    locked, offered, tail = build(plan, wf.get("step_costs") or {}, wf.get("step_requires") or {},
                                  tier=a.tier, paths=paths, profile=a.profile,
                                  tags=[t for t in a.tags.split(",") if t],
                                  manifest=manifest, incidents=incidents)
    if a.mode == "render":
        print(render(locked, offered, tail))
        return 0

    asked = {k.strip() for k in a.keep.split(",") if k.strip()}
    known = {r["key"] for r in locked + offered + tail}
    unknown = sorted(asked - known)
    if unknown:
        print("--keep names steps that are not in this plan: %s\n"
              "Refusing rather than silently declining what you asked to keep."
              % ", ".join(unknown), file=sys.stderr)
        return 2
    kept = asked | {r["key"] for r in locked}
    doc, warn = choices(kept, offered, tail, wf.get("step_requires") or {}, a.actor)
    if not a.actor.strip():
        print("--actor is required: a skip is accountable to a person, not the agent", file=sys.stderr)
        return 2
    for step, need, why in warn:
        print("incoherent: keeping %s while dropping %s — %s" % (step, need, why), file=sys.stderr)
    print(json.dumps(doc, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
