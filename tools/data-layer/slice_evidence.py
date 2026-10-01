#!/usr/bin/env python3
"""Evidence slicer (FR-31, DL-4, ADR-5): one evidence slice per candidate entity.

Evidence files are one per source and type, so an Interpret sub-agent handed whole files would see
every entity's evidence. This script reads candidates.yaml (the mechanical candidate list, edited by
the person) and writes evidence/slices/<entity>.yaml holding only the items that name that entity's
class, stores, keys or fields, each with its origin. Deterministic: the same evidence and candidates
give byte-identical slices.

candidates.yaml:
    candidates:
      - { entity: ent:order, classes: [Order], stores: [orders], fields: [] }

Usage:
    python3 tools/data-layer/slice_evidence.py --data-dir docs/02-design/data
    python3 tools/data-layer/slice_evidence.py --propose   # write candidates.yaml from the code evidence
"""
from __future__ import annotations

import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dl_common import dump_yaml, load_yaml, stamp, parse_ts  # noqa: E402


def kebab(s: str) -> str:
    s = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "-", s)
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def singular(s: str) -> str:
    if s.endswith("ies"):
        return s[:-3] + "y"
    if s.endswith("s") and not s.endswith("ss"):
        return s[:-1]
    return s


def evidence_files(data_dir: str) -> list[tuple[str, dict]]:
    root = os.path.join(data_dir, "evidence")
    out = []
    if not os.path.isdir(root):
        return out
    for dirpath, dirs, names in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d != "slices")
        for n in sorted(names):
            if n.endswith((".yaml", ".yml")):
                rel = os.path.relpath(os.path.join(dirpath, n), data_dir).replace(os.sep, "/")
                out.append((rel, load_yaml(os.path.join(dirpath, n))))
    out.sort(key=lambda t: t[0])
    return out


def propose(data_dir: str) -> dict:
    """Every ORM class, every store literal not already an ORM table, every ddl table and dbt model."""
    cands: dict[str, dict] = {}
    orm_tables = set()
    for rel, doc in evidence_files(data_dir):
        for it in doc.get("items") or []:
            d = it.get("data") or {}
            if it.get("kind") == "orm_entity" and d.get("class") and d.get("table"):
                ent = "ent:%s" % kebab(d["class"])
                c = cands.setdefault(ent, {"entity": ent, "classes": [], "stores": [], "fields": []})
                if d["class"] not in c["classes"]:
                    c["classes"].append(d["class"])
                if d["table"] not in c["stores"]:
                    c["stores"].append(d["table"])
                orm_tables.add(d["table"])
    for rel, doc in evidence_files(data_dir):
        for it in doc.get("items") or []:
            d = it.get("data") or {}
            store = d.get("store") if it.get("kind") in ("store_literal", "count") else (d.get("table") if it.get("kind") == "ddl" else None)
            if store and store not in orm_tables and not any(store in c["stores"] for c in cands.values()):
                base = re.sub(r"[_-]?(cache|table|collection)$", "", store)
                ent = "ent:%s" % kebab(singular(base))
                cands.setdefault(ent, {"entity": ent, "classes": [], "stores": [store], "fields": []})
    return {"schema_version": "1.0", "candidates": [cands[k] for k in sorted(cands)]}


def belongs(item: dict, cand: dict, writer_files: set[str]) -> bool:
    d = item.get("data") or {}
    kind = item.get("kind")
    stores = set(cand.get("stores") or [])
    classes = set(cand.get("classes") or [])
    fields = set(cand.get("fields") or [])
    file = str(item.get("locator", "")).split(":")[0]
    if kind == "orm_entity":
        if d.get("class") in classes or d.get("table") in stores:
            return True
        return any(fk.get("to", "").split(".")[0] in stores for fk in d.get("foreign_keys") or [])
    if kind == "ddl":
        if d.get("table") in stores:
            return True
        return any(fk.get("to", "").split(".")[0] in stores for fk in d.get("foreign_keys") or [])
    if kind in ("store_literal", "read", "write", "key_use", "count", "field_presence", "key_candidates"):
        if d.get("store") in stores:
            return True
        if kind in ("read", "write") and fields and set(d.get("fields") or []) & fields:
            return True
        if kind == "field_presence" and fields and set((d.get("present_pct") or {}).keys()) & fields:
            return True
        if kind in ("read", "write", "store_literal", "key_use") and file in writer_files:
            return True
        return False
    if kind == "join":
        return d.get("left") in stores or d.get("right") in stores
    if kind == "key_overlap":
        return str(d.get("left", "")).split(".")[0] in stores or str(d.get("right", "")).split(".")[0] in stores
    return False


def slices(data_dir: str, candidates: list[dict], at) -> dict[str, dict]:
    files = evidence_files(data_dir)
    out = {}
    for cand in candidates:
        stores = set(cand.get("stores") or [])
        # the files that write one of this entity's stores: their reads are this entity's lineage evidence
        writer_files = set()
        for rel, doc in files:
            for it in doc.get("items") or []:
                if it.get("kind") == "write" and (it.get("data") or {}).get("store") in stores:
                    writer_files.add(str(it.get("locator", "")).split(":")[0])
        items = []
        for rel, doc in files:
            for it in doc.get("items") or []:
                if belongs(it, cand, writer_files):
                    items.append({"id": it["id"], "kind": it["kind"], "locator": it["locator"], "data": it["data"],
                                  "origin": {"file": rel, "item": it["id"]}})
        name = cand["entity"].split(":", 1)[1]
        out[name] = {"schema_version": "1.0", "evidence_type": "slice", "source": "src:app", "taken_at": stamp(at),
                     "adapter": {"name": "slice_evidence.py", "version": "1.0.0"},
                     "access": {"mode": "offline", "environment": "offline-export", "read_only": True},
                     "entity": cand["entity"], "items": items}
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", default="docs/02-design/data")
    ap.add_argument("--candidates", help="default <data-dir>/candidates.yaml")
    ap.add_argument("--propose", action="store_true", help="write candidates.yaml from the evidence and stop")
    ap.add_argument("--taken-at")
    a = ap.parse_args(argv)
    cpath = a.candidates or os.path.join(a.data_dir, "candidates.yaml")
    if a.propose:
        doc = propose(a.data_dir)
        dump_yaml(cpath, doc)
        print("slice_evidence: %d candidate(s) -> %s (edit, then run without --propose)" % (len(doc["candidates"]), cpath))
        for c in doc["candidates"]:
            print("  %-24s classes=%s stores=%s" % (c["entity"], c["classes"], c["stores"]))
        return 0
    if not os.path.exists(cpath):
        print("slice_evidence: no %s; run with --propose first" % cpath)
        return 2
    cands = [c for c in load_yaml(cpath).get("candidates") or [] if isinstance(c, dict) and c.get("entity")]
    out = slices(a.data_dir, cands, parse_ts(a.taken_at))
    folder = os.path.join(a.data_dir, "evidence", "slices")
    os.makedirs(folder, exist_ok=True)
    for n in os.listdir(folder):
        if n.endswith(".yaml") and n[:-5] not in out:
            os.remove(os.path.join(folder, n))
    for name, doc in out.items():
        dump_yaml(os.path.join(folder, name + ".yaml"), doc)
        print("  %-20s %d item(s)%s" % (name, len(doc["items"]), "" if doc["items"] else "  (empty: nothing names it)"))
    print("slice_evidence: %d slice(s) -> %s" % (len(out), folder))
    return 0


if __name__ == "__main__":
    sys.exit(main())
