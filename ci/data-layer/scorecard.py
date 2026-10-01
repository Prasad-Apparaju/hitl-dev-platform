#!/usr/bin/env python3
"""Data-layer scorecard (FR-31, DL-7, DL-2). Design: docs/design/data-layer/03-lld.md §5.

Reads the four files, questions.yaml, sources.yaml and the evidence folder; computes the ten metrics;
writes scorecard.yaml (the next run's baseline) and scorecard.md (a one-page plain-English report);
prints the report. With --baseline it diffs every metric and marks regressions; the exit is 1 only
with --strict and a regression, else 0. A missing baseline is reported, never a pass or a regression.

The scorecard is a script, not a model: the same files give the same numbers. The validator is the
guard on the files' shape; this script reads them leniently and reports what it can compute.

Usage:
    python3 ci/data-layer/scorecard.py
    python3 ci/data-layer/scorecard.py --baseline docs/02-design/data/scorecard.yaml --strict
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import statistics
import sys

try:
    import yaml
except ImportError:  # pragma: no cover
    print("ERROR: pyyaml required. Run: pip install pyyaml")
    sys.exit(2)

DEFAULTS = {"blocking": False, "stale_evidence_days": 90}
# metric -> direction that counts as a regression ("down" = a fall regresses, "up" = a rise regresses)
REGRESSES = {
    "verification_rate.entities": "down", "verification_rate.fields": "down", "verification_rate.edges": "down",
    "entities_without_mapping": "up", "sources_not_extracted": "up", "evidence_age_days.oldest": "stale",
    "open_high_findings": "up", "negative_edges": "up", "answerable.yes": "down", "collisions": "up",
}


def _load(path):
    try:
        with open(path, encoding="utf-8") as f:
            d = yaml.safe_load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, yaml.YAMLError):
        return {}


def _lst(d, key):
    v = d.get(key) if isinstance(d, dict) else None
    return [x for x in v if isinstance(x, dict)] if isinstance(v, list) else []


def _parse_ts(v):
    if isinstance(v, dt.datetime):
        return v if v.tzinfo else v.replace(tzinfo=dt.timezone.utc)
    if isinstance(v, str):
        try:
            return dt.datetime.fromisoformat(v.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _rate(items):
    items = list(items)
    if not items:
        return 0.0
    return round(sum(1 for c in items if c == "confirmed") / len(items), 3)


def config(path: str) -> dict:
    cfg = dict(DEFAULTS)
    d = _load(path) if path and os.path.exists(path) else {}
    block = d.get("data_layer") if isinstance(d, dict) else None
    if isinstance(block, dict):
        for k in DEFAULTS:
            if k in block:
                cfg[k] = block[k]
    return cfg


def compute(data_dir: str, run_at: dt.datetime) -> dict:
    ont = _lst(_load(os.path.join(data_dir, "ontology.yaml")), "entities")
    maps = _lst(_load(os.path.join(data_dir, "mappings.yaml")), "mappings")
    lin = _load(os.path.join(data_dir, "lineage.yaml"))
    edges = _lst(lin, "edges")
    fnds = _lst(_load(os.path.join(data_dir, "findings.yaml")), "findings")
    qs = _lst(_load(os.path.join(data_dir, "questions.yaml")), "questions")
    srcs = _lst(_load(os.path.join(data_dir, "sources.yaml")), "sources")

    fields = [f.get("confidence") for m in maps for f in (m.get("fields") or []) if isinstance(f, dict)]
    mapped = {m.get("entity") for m in maps}
    no_map = sorted(e["id"] for e in ont if e.get("id") and e["id"] not in mapped)
    unext = sorted(s["id"] for s in srcs if s.get("status") == "declared-not-extracted" and s.get("id"))

    ages = []
    root = os.path.join(data_dir, "evidence")
    if os.path.isdir(root):
        for dp, _, names in os.walk(root):
            if os.path.basename(dp) == "slices":
                continue
            for n in names:
                if n.endswith((".yaml", ".yml")):
                    t = _parse_ts(_load(os.path.join(dp, n)).get("taken_at"))
                    if t:
                        ages.append(max(0, (run_at - t).days))
    age = {"oldest": max(ages), "newest": min(ages), "median": int(statistics.median(ages))} if ages else \
          {"oldest": None, "newest": None, "median": None}

    open_high = sum(1 for f in fnds if f.get("severity") == "high" and f.get("status") == "open")
    neg_words = ("never", "not", "no ", "missing", "empty")
    neg_edges = sum(1 for e in edges if isinstance(e.get("rule"), str) and e["rule"].strip().lower().startswith(neg_words))

    conf = {}
    for e in ont:
        conf[e.get("id")] = e.get("confidence")
    for m in maps:
        conf[m.get("id")] = m.get("confidence")
    for e in edges:
        conf[e.get("id")] = e.get("confidence")
    ans = {"yes": 0, "no": 0, "unconfirmed": 0, "total": len(qs)}
    waiting = {}
    for q in qs:
        needs = q.get("needs") or {}
        ids = [i for k in ("entities", "mappings", "edges") for i in (needs.get(k) or []) if isinstance(needs, dict)]
        if not isinstance(q.get("confirmed_by"), dict):
            ans["unconfirmed"] += 1
            continue
        missing = [i for i in ids if conf.get(i) not in ("confirmed", "inferred")]
        if missing:
            ans["no"] += 1
            waiting[q.get("id")] = missing
        else:
            ans["yes"] += 1

    coll = []
    syn = {}
    for e in ont:
        for s in (e.get("synonyms") or []):
            if isinstance(s, str):
                syn.setdefault(s.strip().lower(), set()).add(e.get("id"))
    for s, owners in sorted(syn.items()):
        if len(owners) > 1:
            o = sorted(owners)
            for i in range(len(o)):
                for j in range(i + 1, len(o)):
                    coll.append([o[i], o[j], "synonym: %s" % s])
    keys = {}
    for m in maps:
        st = m.get("store") if isinstance(m.get("store"), dict) else {}
        nk = m.get("natural_key")
        if st.get("source") and isinstance(nk, list) and nk:
            keys.setdefault((st["source"], tuple(nk)), set()).add(m.get("entity"))
    for (src, nk), owners in sorted(keys.items()):
        if len(owners) > 1:
            o = sorted(owners)
            for i in range(len(o)):
                for j in range(i + 1, len(o)):
                    coll.append([o[i], o[j], "natural key %s in %s" % (list(nk), src)])
    coll.sort()

    return {
        "verification_rate": {"entities": _rate(e.get("confidence") for e in ont),
                              "fields": _rate(fields),
                              "edges": _rate(e.get("confidence") for e in edges)},
        "entities_without_mapping": no_map,
        "sources_not_extracted": unext,
        "evidence_age_days": age,
        "open_high_findings": open_high,
        "negative_edges": neg_edges,
        "answerable": ans,
        "collisions": coll,
        "_waiting": waiting,
        "_open_high": sorted(f["id"] for f in fnds if f.get("severity") == "high" and f.get("status") == "open" and f.get("id")),
    }


def _flat(m: dict) -> dict:
    out = {}
    for k, v in m.items():
        if k.startswith("_"):
            continue
        if isinstance(v, dict):
            for k2, v2 in v.items():
                out["%s.%s" % (k, k2)] = v2
        elif isinstance(v, list):
            out[k] = len(v)
        else:
            out[k] = v
    return out


def diff(new: dict, base: dict | None, stale_days: int) -> list[dict]:
    """One row per metric: {metric, before, after, regression}."""
    rows = []
    n, b = _flat(new), _flat(base or {})
    for k, after in n.items():
        before = b.get(k) if base is not None else None
        reg = False
        if k in REGRESSES and base is not None and before is not None and after is not None:
            d = REGRESSES[k]
            reg = (d == "down" and after < before) or (d == "up" and after > before)
        if k == "evidence_age_days.oldest" and isinstance(after, int) and after > stale_days:
            reg = True
        rows.append({"metric": k, "before": before, "after": after, "regression": reg})
    return rows


def report(metrics: dict, rows: list[dict], mode: str, baseline_note: str) -> str:
    regs = [r for r in rows if r["regression"]]
    lines = ["# Data layer scorecard", "", "Mode: %s. %s" % (mode, baseline_note), ""]
    if regs:
        lines += ["## Regressions", ""]
        for r in regs:
            lines.append("- %s went from %s to %s." % (r["metric"], r["before"], r["after"]))
        lines.append("")
    lines += ["## Metrics", "", "| Metric | Before | After |", "|---|---|---|"]
    for r in rows:
        lines.append("| %s | %s | %s |" % (r["metric"], "" if r["before"] is None else r["before"], r["after"]))
    lines.append("")
    w = metrics.get("_waiting") or {}
    if w:
        lines += ["## Questions not answerable", ""]
        for q, ids in sorted(w.items()):
            lines.append("- %s waits on %s." % (q, ", ".join(ids)))
        lines.append("")
    if metrics["answerable"]["unconfirmed"]:
        lines += ["%d question(s) have a needs list nobody confirmed; they count as not answerable." % metrics["answerable"]["unconfirmed"], ""]
    if metrics["collisions"]:
        lines += ["## Collisions", ""]
        for a, b2, why in metrics["collisions"]:
            lines.append("- %s and %s share %s." % (a, b2, why))
        lines.append("")
    if metrics.get("_open_high"):
        lines += ["## Open high-severity findings", ""]
        for f in metrics["_open_high"]:
            lines.append("- %s" % f)
        lines.append("")
    if metrics["sources_not_extracted"]:
        lines += ["Declared and not extracted: %s." % ", ".join(metrics["sources_not_extracted"]), ""]
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", default="docs/02-design/data")
    ap.add_argument("--baseline", help="a previous scorecard.yaml to diff against")
    ap.add_argument("--config", default=".hitl/config.yaml")
    ap.add_argument("--out", help="where to write scorecard.yaml (default: <data-dir>/scorecard.yaml)")
    ap.add_argument("--report", help="where to write scorecard.md (default: <data-dir>/scorecard.md)")
    ap.add_argument("--run-at", help="ISO timestamp for the run (default: now, UTC)")
    ap.add_argument("--strict", action="store_true", help="exit 1 on a regression")
    ap.add_argument("--no-write", action="store_true", help="print only")
    a = ap.parse_args(argv)
    if not os.path.isdir(a.data_dir):
        print("data layer: absent (%s)" % a.data_dir)
        return 0
    cfg = config(a.config)
    mode = "blocking" if cfg.get("blocking") is True else "advisory"
    run_at = _parse_ts(a.run_at) if a.run_at else dt.datetime.now(dt.timezone.utc)
    if run_at is None:
        print("ERROR: --run-at is not an ISO timestamp")
        return 2
    metrics = compute(a.data_dir, run_at)
    base = None
    note = "No baseline given; nothing to diff."
    if a.baseline:
        if os.path.exists(a.baseline):
            bd = _load(a.baseline)
            base = bd.get("metrics") if isinstance(bd.get("metrics"), dict) else None
            note = "Diffed against %s (run %s)." % (a.baseline, bd.get("run_at")) if base else "Baseline %s has no metrics; nothing to diff." % a.baseline
        else:
            note = "Baseline %s does not exist; nothing to diff." % a.baseline
    try:
        stale = int(cfg.get("stale_evidence_days", 90))
    except (TypeError, ValueError):
        stale = 90
    rows = diff(metrics, base, stale)
    text = report(metrics, rows, mode, note)
    print(text)
    if not a.no_write:
        out = a.out or os.path.join(a.data_dir, "scorecard.yaml")
        rep = a.report or os.path.join(a.data_dir, "scorecard.md")
        public = {k: v for k, v in metrics.items() if not k.startswith("_")}
        with open(out, "w", encoding="utf-8") as f:
            yaml.safe_dump({"schema_version": "1.0", "run_at": run_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
                            "mode": mode, "metrics": public}, f, sort_keys=False)
        with open(rep, "w", encoding="utf-8") as f:
            f.write(text + "\n")
    if a.strict and any(r["regression"] for r in rows):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
