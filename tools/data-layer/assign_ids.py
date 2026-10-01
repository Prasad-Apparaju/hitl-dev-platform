#!/usr/bin/env python3
"""ID assigner (FR-31, ADR-5): number edges and findings after Fold.

Isolated Interpret sub-agents cannot allocate integers, so edges and findings leave Fold without an
`id`. This script reads the previous lineage.yaml and findings.yaml (if any), keeps the ID of every
edge matched by (relation, subject, object) and every finding matched by (kind, about, statement),
and gives each new one the next integer above the previous maximum. IDs are never reused.

Usage:
    python3 tools/data-layer/assign_ids.py --data-dir docs/02-design/data [--previous <dir with the old files>]
"""
from __future__ import annotations

import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dl_common import dump_yaml, load_yaml  # noqa: E402


def _num(ident) -> int:
    m = re.fullmatch(r"(?:lin|fnd):(\d+)", str(ident))
    return int(m.group(1)) if m else 0


def edge_key(e: dict):
    return (e.get("relation"), e.get("subject"), e.get("object"))


def finding_key(f: dict):
    about = f.get("about")
    return (f.get("kind"), tuple(sorted(about)) if isinstance(about, list) else None, (f.get("statement") or "").strip())


def assign(new: list[dict], previous: list[dict], prefix: str, key) -> tuple[list[dict], int, int]:
    """Returns (entries with ids, kept, assigned)."""
    by_key = {key(p): p.get("id") for p in previous if isinstance(p, dict) and p.get("id")}
    used = {str(p.get("id")) for p in previous if isinstance(p, dict) and p.get("id")}
    used |= {str(n.get("id")) for n in new if isinstance(n, dict) and n.get("id")}
    nxt = max([_num(i) for i in used] + [0]) + 1
    kept = assigned = 0
    for n in new:
        if not isinstance(n, dict) or n.get("id"):
            continue
        k = key(n)
        if k in by_key and by_key[k] not in {str(x.get("id")) for x in new if x is not n}:
            n["id"] = by_key[k]
            kept += 1
        else:
            while "%s:%d" % (prefix, nxt) in used:
                nxt += 1
            n["id"] = "%s:%d" % (prefix, nxt)
            used.add(n["id"])
            nxt += 1
            assigned += 1
        # put id first so the file reads like the template
        n_copy = {"id": n.pop("id")}
        n_copy.update(n)
        n.clear()
        n.update(n_copy)
    return new, kept, assigned


def run(data_dir: str, previous_dir: str | None) -> dict:
    prev = previous_dir or data_dir
    out = {}
    for name, listkey, prefix, key in (("lineage.yaml", "edges", "lin", edge_key),
                                        ("findings.yaml", "findings", "fnd", finding_key)):
        path = os.path.join(data_dir, name)
        if not os.path.exists(path):
            continue
        doc = load_yaml(path)
        entries = doc.get(listkey) if isinstance(doc.get(listkey), list) else []
        ppath = os.path.join(prev, name)
        pdoc = load_yaml(ppath) if os.path.exists(ppath) and os.path.abspath(ppath) != os.path.abspath(path) else {}
        previous = pdoc.get(listkey) if isinstance(pdoc.get(listkey), list) else []
        if previous_dir is None:
            previous = [e for e in entries if isinstance(e, dict) and e.get("id")]
        _, kept, assigned = assign(entries, previous, prefix, key)
        doc[listkey] = entries
        dump_yaml(path, doc)
        out[name] = {"kept": kept, "assigned": assigned}
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", default="docs/02-design/data")
    ap.add_argument("--previous", help="directory holding the previous lineage.yaml and findings.yaml")
    a = ap.parse_args(argv)
    for name, r in run(a.data_dir, a.previous).items():
        print("assign_ids: %s kept %d, assigned %d" % (name, r["kept"], r["assigned"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
