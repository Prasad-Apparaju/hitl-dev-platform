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




def sizable(costs, plan):
    """Is there enough data to lighten this plan responsibly?

    Without `step_costs` every step ranks the same, so the order collapses to catalog order — and
    catalog order is CHRONOLOGY, not importance. The first eight steps are the Design phase and the
    tail is every review, verification and the rollout plan. A project that upgraded but has not
    refreshed its ci/first-pass/workflows.yaml would have had code review and QA silently dropped.

    No basis to rank means no collapsing: show the whole plan, exactly as before. A project gets the
    lighter path when it has opted in, never as a side effect of missing data.
    """
    keys = {s.get("key") for s in (plan or [])}
    return bool(keys and len([k for k in keys if (costs or {}).get(k)]) >= max(1, len(keys) // 2))


def build(plan, costs, requires, *, tier, paths, profile, tags, manifest, incidents):
    risky = R.risky_domains(manifest, incidents)
    ranked = R.rank_plan(plan, costs, tier=tier, paths=paths, profile=profile, tags=tags,
                         multi_domain=len(source_paths(manifest)) > 1,
                         risky_domain=R.touches_risky(paths, risky))
    locked = [r for r in ranked if r["locked"]]
    rest = [r for r in ranked if not r["locked"]]
    if not sizable(costs, plan):
        return locked, rest, []          # nothing collapses; the plan is shown whole
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


def apply_to_change(change_path, kept, offered, tail, requires, actor):
    """Write the dispositions into the change file that already exists.

    The selection runs at apply-change step 3a, AFTER intake created the change file. Writing a
    choices file here would hand off to start-change step 6, which has already run — so the record
    would be written for a consumer that never comes. Update the file in place instead: mark each
    unkept step `skipped`, and append an attributed entry to `skips[]`, which is what the
    fail-closed validator reads.
    """
    doc = _load(change_path)
    if not doc:
        return None, "no change file at %s — intake creates it; run /hitl:dev-start-change first" % change_path
    kept = set(kept or ())
    unkept = {r["key"]: r for r in list(offered) + list(tail) if r["key"] not in kept}
    steps = ((doc.get("workflow") or {}).get("steps")) or []
    if not steps:
        return None, "the change file has no workflow.steps to disposition"

    existing = {str(e.get("step")) for e in (doc.get("skips") or []) if isinstance(e, dict)}
    ts = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)\
        .isoformat(timespec="seconds")
    added = []
    for st in steps:
        k = st.get("key")
        if k in unkept and str(st.get("status")) not in ("done",):
            st["status"] = "skipped"
            if k not in existing:
                r = unkept[k]
                added.append({"step": k, "crit": r["step"].get("crit", "standard"),
                              "disposition": "decline", "actor": actor, "ts": ts,
                              "reason": "not selected at right-sizing (rank %s): %s"
                                        % (r["rank"], r["protects"] or "no reason recorded")})
    doc.setdefault("skips", []).extend(added)
    return doc, None


def _load(path):
    try:
        with open(path) as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["render", "choices", "apply"])
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
    ap.add_argument("--change", default=".hitl/current-change.yaml")
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
    if a.mode == "apply":
        doc, err = apply_to_change(a.change, kept, offered, tail,
                                   wf.get("step_requires") or {}, a.actor)
        if err:
            print(err, file=sys.stderr)
            return 2
        for step, need, why in R.incoherent(kept, wf.get("step_requires") or {}):
            print("incoherent: keeping %s while dropping %s — %s" % (step, need, why), file=sys.stderr)
        with open(a.change, "w") as f:
            yaml.safe_dump(doc, f, sort_keys=False, width=100)
        print("wrote %d skip records to %s" % (len(doc.get("skips") or []), a.change))
        return 0
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
