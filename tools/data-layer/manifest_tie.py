#!/usr/bin/env python3
"""Manifest tie (FR-31, DL-6, ADR-1, LLD §7): derive the manifest's boundary entities from mappings.

For each mapping, the domain of each path in written_by and read_by is the manifest domain whose
files list contains it. An entity written from domain D and read from any other domain E is a
boundary entity of D consumed by E. Writes domains.<D>.boundary_entities.<Name> with shape (field
names and types) and consumed_by; keeps human-added keys on an existing entry; lists paths no domain
owns as unowned. The manifest generator overwrites the file on its own re-run, so run this after it.

Usage:
    python3 tools/data-layer/manifest_tie.py --data-dir docs/02-design/data --manifest docs/system-manifest.yaml
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dl_common import dump_yaml, load_yaml  # noqa: E402


def derive(mappings: list[dict], entities: dict[str, dict], domains: dict) -> tuple[dict, list[str]]:
    file_domain = {}
    for dname, dom in (domains or {}).items():
        for f in (dom or {}).get("files") or [] if isinstance(dom, dict) else []:
            file_domain[str(f)] = dname
    block: dict[str, dict] = {}
    unowned: list[str] = []
    for m in mappings:
        ent = entities.get(m.get("entity")) or {}
        name = ent.get("name") or str(m.get("entity", "")).split(":")[-1]
        writers, readers = set(), set()
        for p in m.get("written_by") or []:
            d = file_domain.get(str(p))
            (writers.add(d) if d else unowned.append(str(p)))
        for p in m.get("read_by") or []:
            d = file_domain.get(str(p))
            (readers.add(d) if d else unowned.append(str(p)))
        for w in sorted(writers):
            consumers = sorted(r for r in readers if r != w)
            if not consumers:
                continue
            shape = "".join("%s: %s\n" % (f.get("name"), f.get("type") or "unknown") for f in (m.get("fields") or []) if isinstance(f, dict))
            entry = block.setdefault(w, {}).setdefault(name, {"shape": shape, "consumed_by": []})
            entry["shape"] = shape
            for c in consumers:
                if c not in entry["consumed_by"]:
                    entry["consumed_by"].append(c)
    return block, sorted(set(unowned))


def apply(manifest: dict, block: dict) -> dict:
    domains = manifest.setdefault("domains", {})
    for dname, dom in list(domains.items()):
        if not isinstance(dom, dict):
            continue
        existing = dom.get("boundary_entities") if isinstance(dom.get("boundary_entities"), dict) else {}
        derived = block.get(dname, {})
        merged = {}
        for name, entry in derived.items():
            old = existing.get(name) if isinstance(existing.get(name), dict) else {}
            new = dict(old)              # human-added keys survive
            new["shape"] = entry["shape"]
            new["consumed_by"] = entry["consumed_by"]
            merged[name] = new
        if merged:
            dom["boundary_entities"] = merged
        elif "boundary_entities" in dom and not existing:
            del dom["boundary_entities"]
        elif existing and not merged:
            dom["boundary_entities"] = existing   # nothing derived; leave what a person wrote
    return manifest


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", default="docs/02-design/data")
    ap.add_argument("--manifest", default="docs/system-manifest.yaml")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    if not os.path.exists(a.manifest):
        print("manifest_tie: no manifest at %s" % a.manifest)
        return 2
    maps = [m for m in load_yaml(os.path.join(a.data_dir, "mappings.yaml")).get("mappings") or [] if isinstance(m, dict)]
    ents = {e.get("id"): e for e in load_yaml(os.path.join(a.data_dir, "ontology.yaml")).get("entities") or [] if isinstance(e, dict)}
    manifest = load_yaml(a.manifest)
    block, unowned = derive(maps, ents, manifest.get("domains") or {})
    for d, names in block.items():
        for n, e in names.items():
            print("  %s.boundary_entities.%s consumed_by %s" % (d, n, e["consumed_by"]))
    if unowned:
        print("  unowned paths (in no manifest domain): %s" % ", ".join(unowned))
    if not a.dry_run:
        dump_yaml(a.manifest, apply(manifest, block))
        print("manifest_tie: wrote %s" % a.manifest)
    return 0


if __name__ == "__main__":
    sys.exit(main())
