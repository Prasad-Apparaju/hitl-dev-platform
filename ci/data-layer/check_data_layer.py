#!/usr/bin/env python3
"""Data-layer validator (FR-31, EPIC #131). Design: docs/design/data-layer/03-lld.md §4.

Reads docs/02-design/data/ (six files, evidence/, interpretations/, run.log), the manifest's
boundary_entities and the data layer's own waiver file, and checks the rules the design lists. A
finding is {code, message, waivable, locus}. Exit 2 when any non-waivable finding exists, 1 with
--strict when any waivable one does, else 0. Any input it cannot parse is MALFORMED, never a traceback.

Every key list and enum comes from data-layer.schema.yaml next to this file (the shipped copy of
ai/shared/templates/data-layer/data-layer.schema.yaml). Nothing here is a model; a different model
can re-run every stage from the same files and this validator says the same thing.

Usage:
    python3 ci/data-layer/check_data_layer.py
    python3 ci/data-layer/check_data_layer.py --data-dir docs/02-design/data --manifest docs/system-manifest.yaml
    python3 ci/data-layer/check_data_layer.py --strict --tier 2 --json
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys

try:
    import yaml
except ImportError:  # pragma: no cover
    print("ERROR: pyyaml required. Run: pip install pyyaml")
    sys.exit(2)

HERE = os.path.dirname(os.path.abspath(__file__))
MAX_BYTES = 50 * 1024 * 1024
FOUR = ("ontology.yaml", "mappings.yaml", "lineage.yaml", "findings.yaml")
SIX = ("sources.yaml", "questions.yaml") + FOUR

# Waivable codes. Everything else is the framework's guarantee and fails closed.
WAIVABLE = {
    "BOUNDARY_NOT_IN_ONTOLOGY", "EDGE_RULE_IS_CODE", "EDGE_READS_NEGATIVE",
    "QUESTION_NEEDS_UNKNOWN", "QUESTION_NEEDS_UNCONFIRMED", "FILE_MISSING",
}
# Codes a waiver row may name. A row naming any other code is ignored (NEG-25).
WAIVER_ELIGIBLE = {"BOUNDARY_NOT_IN_ONTOLOGY"}


class Malformed(Exception):
    pass


# ---------------------------------------------------------------------------
# Loading: duplicate keys, size, symlinks and wrong shapes are MALFORMED
# ---------------------------------------------------------------------------

class _StrictLoader(yaml.SafeLoader):
    pass


def _no_dup(loader, node, deep=False):
    seen = set()
    for k, _ in node.value:
        key = loader.construct_object(k, deep=deep)
        try:
            hashable = key
            if hashable in seen:
                raise Malformed("duplicate key %r" % (key,))
        except TypeError:
            raise Malformed("unhashable key")
        seen.add(key)
    return yaml.SafeLoader.construct_mapping(loader, node, deep)


_StrictLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _no_dup)


def _inside(root: str, path: str) -> bool:
    r = os.path.realpath(root)
    p = os.path.realpath(path)
    return p == r or p.startswith(r + os.sep)


def load_yaml(path: str, root: str, want: type = dict):
    """Parse one YAML file fail-closed. `root` bounds symlinks."""
    if not _inside(root, path):
        raise Malformed("outside the data directory")
    if not os.path.isfile(path):
        raise Malformed("not a file")
    if os.path.getsize(path) > MAX_BYTES:
        raise Malformed("larger than %d bytes" % MAX_BYTES)
    try:
        with open(path, "rb") as f:
            raw = f.read()
        text = raw.decode("utf-8")
    except (OSError, UnicodeDecodeError) as e:
        raise Malformed("cannot read as UTF-8: %s" % e.__class__.__name__)
    if "\t" in text.split("\n", 1)[0] or re.search(r"^\t", text, re.M):
        raise Malformed("tab indentation")
    try:
        data = yaml.load(text, Loader=_StrictLoader)
    except Malformed:
        raise
    except yaml.YAMLError as e:
        raise Malformed("YAML error: %s" % str(e).splitlines()[0])
    if data is None:
        raise Malformed("empty file")
    if not isinstance(data, want):
        raise Malformed("top level is %s, expected %s" % (type(data).__name__, want.__name__))
    return data


# ---------------------------------------------------------------------------
# The checker
# ---------------------------------------------------------------------------

def kebab(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(name).lower()).strip("-")


def _prefix(ident) -> str:
    return str(ident).split(":", 1)[0] if isinstance(ident, str) and ":" in ident else ""


class Checker:
    def __init__(self, data_dir: str, schema: dict, manifest_path: str | None,
                 waivers_path: str | None, tier: int, today: dt.date | None = None):
        self.d = data_dir
        self.s = schema
        self.core = schema["core"]
        self.files = schema["files"]
        self.manifest_path = manifest_path
        self.waivers_path = waivers_path
        self.tier = tier
        self.today = today or dt.date.today()
        self.findings: list[dict] = []
        self.ids: dict[str, str] = {}          # id -> where
        self.evidence: dict[str, dict] = {}    # rel file -> {item id -> item}
        self.slices: set[str] = set()
        self.docs: dict[str, dict] = {}
        self.sources: dict[str, dict] = {}
        self.entities: dict[str, dict] = {}
        self.mappings: dict[str, dict] = {}
        self.activities: dict[str, dict] = {}
        self.edges: dict[str, dict] = {}
        self.fnds: dict[str, dict] = {}

    # -- findings -----------------------------------------------------------
    def add(self, code: str, locus: str, msg: str):
        self.findings.append({"code": code, "locus": str(locus), "message": msg,
                              "waivable": code in WAIVABLE})

    # -- helpers ------------------------------------------------------------
    def rel(self, path: str) -> str:
        return os.path.relpath(path, self.d).replace(os.sep, "/")

    def _load(self, name: str, want=dict):
        path = os.path.join(self.d, name)
        try:
            return load_yaml(path, self.d, want)
        except Malformed as e:
            self.add("MALFORMED", name, "%s: %s" % (name, e))
            return None

    def keys_ok(self, obj, allowed: list, required: list, locus: str, label: str) -> bool:
        if not isinstance(obj, dict):
            self.add("MALFORMED", locus, "%s is %s, expected a mapping" % (label, type(obj).__name__))
            return False
        ok = True
        for k in obj:
            if k not in allowed:
                self.add("SCHEMA_UNKNOWN_FIELD", locus, "%s has a key the schema does not list: %r" % (label, k))
                ok = False
        for k in required:
            if k not in obj and k not in ("confidence", "evidence"):   # those two are the core's own codes
                self.add("MALFORMED", locus, "%s is missing required key %r" % (label, k))
                ok = False
        return ok

    def list_of_dicts(self, obj, locus: str, label: str) -> list:
        if obj is None:
            return []
        if not isinstance(obj, list) or any(not isinstance(x, dict) for x in obj):
            self.add("MALFORMED", locus, "%s must be a list of mappings" % label)
            return []
        return obj

    def register_id(self, ident, prefix: str, locus: str) -> bool:
        if not isinstance(ident, str) or _prefix(ident) != prefix or len(ident) <= len(prefix) + 1:
            self.add("MALFORMED", locus, "id %r must start with %r" % (ident, prefix + ":"))
            return False
        if ident in self.ids:
            self.add("ID_DUPLICATE", ident, "%s is defined twice (%s and %s)" % (ident, self.ids[ident], locus))
            return False
        self.ids[ident] = locus
        return True

    # -- the shared core on one assertion ------------------------------------
    def assertion(self, obj: dict, locus: str, in_four: bool = True, inputs: list | None = None,
                  model_written: bool = False):
        conf = obj.get("confidence")
        if conf not in self.core["confidence"]:
            self.add("CONFIDENCE_UNKNOWN", locus, "confidence %r is not one of %s" % (conf, self.core["confidence"]))
        if model_written and conf == "confirmed":
            self.add("MODEL_WROTE_CONFIRMED", locus, "an interpretation proposes a confirmed entry; only a person or a verification run promotes")
        if conf == "confirmed" and not model_written:
            cbk = obj.get("confirmed_by")
            spec = self.core["confirmed_by"]
            if not isinstance(cbk, dict) or any(not cbk.get(k) for k in spec["required"]) \
                    or cbk.get("how") not in self.core["confirmed_how"]:
                self.add("CONFIRMED_WITHOUT_PROMOTER", locus, "confirmed with no complete confirmed_by {who, at, how}")
        ev = obj.get("evidence")
        if not isinstance(ev, list) or not ev:
            self.add("NO_EVIDENCE", locus, "an assertion with no evidence is not written")
            return
        for i, ref in enumerate(ev):
            rl = "%s evidence[%d]" % (locus, i)
            if not isinstance(ref, dict) or set(ref) != {"file", "item"}:
                self.add("MALFORMED", rl, "an evidence reference is {file, item}")
                continue
            f, item = ref["file"], ref["item"]
            if inputs is not None and f not in inputs:
                self.add("CITATION_OUTSIDE_INPUTS", rl, "cites %s, which is not in the interpretation's inputs" % f)
                continue
            if in_four and f in self.slices:
                self.add("EVIDENCE_UNRESOLVED", rl, "the four files cite origin evidence, not a slice (%s)" % f)
                continue
            items = self.evidence.get(f)
            if items is None:
                if inputs is not None and not f.startswith("evidence/"):
                    continue  # the schema or template handed to the sub-agent; not an evidence file
                self.add("EVIDENCE_UNRESOLVED", rl, "evidence file %s does not exist or did not parse" % f)
            elif item not in items:
                self.add("EVIDENCE_UNRESOLVED", rl, "item %s is not in %s" % (item, f))

    # -- evidence files and run.log -------------------------------------------
    def load_evidence(self):
        root = os.path.join(self.d, "evidence")
        if not os.path.isdir(root):
            return
        spec = self.files["evidence"]
        for dirpath, _, names in os.walk(root):
            for n in sorted(names):
                if not n.endswith((".yaml", ".yml")):
                    continue
                path = os.path.join(dirpath, n)
                rel = self.rel(path)
                try:
                    doc = load_yaml(path, self.d)
                except Malformed as e:
                    self.add("MALFORMED", rel, "%s: %s" % (rel, e))
                    continue
                if not self.keys_ok(doc, spec["top"], spec["required"], rel, rel):
                    continue
                et = doc.get("evidence_type")
                if et not in self.core["evidence_types"]:
                    self.add("EVIDENCE_TYPE_UNKNOWN", rel, "evidence_type %r is not one of the listed types" % et)
                if et == "slice":
                    self.slices.add(rel)
                acc = doc.get("access")
                if self.keys_ok(acc, spec["access"]["keys"], spec["access"]["required"], rel, rel + " access"):
                    if acc.get("read_only") is not True:
                        self.add("WRITE_ACCESS_RECORDED", rel, "access.read_only is not true")
                    if acc.get("mode") == "live":
                        au = acc.get("authorization")
                        if not isinstance(au, dict) or not au.get("by") or not au.get("at"):
                            self.add("LIVE_WITHOUT_AUTHORIZATION", rel, "a live read with no authorization {by, at}")
                items = self.list_of_dicts(doc.get("items"), rel, rel + " items")
                index = {}
                for i, it in enumerate(items):
                    il = "%s items[%d]" % (rel, i)
                    if not self.keys_ok(it, spec["item"]["keys"], spec["item"]["required"], il, il):
                        continue
                    iid = it.get("id")
                    if not isinstance(iid, str) or _prefix(iid) != "ev":
                        self.add("MALFORMED", il, "item id %r must start with 'ev:'" % (iid,))
                        continue
                    if iid in index:
                        self.add("ID_DUPLICATE", iid, "%s appears twice in %s" % (iid, rel))
                    index[iid] = it
                    if et == "slice":
                        o = it.get("origin")
                        if not isinstance(o, dict) or set(o) != {"file", "item"}:
                            self.add("MALFORMED", il, "a slice item carries origin {file, item}")
                self.evidence[rel] = index
        # slice origins resolve
        for rel in sorted(self.slices):
            for iid, it in self.evidence[rel].items():
                o = it.get("origin") or {}
                if o.get("file") not in self.evidence or o.get("item") not in self.evidence.get(o.get("file"), {}):
                    self.add("EVIDENCE_UNRESOLVED", "%s %s" % (rel, iid), "slice origin %s does not resolve" % (o,))
        log = os.path.join(self.d, "run.log")
        if os.path.isfile(log):
            allowed = set(self.core["read_only_calls"]) | {"scan"}
            with open(log, encoding="utf-8", errors="replace") as f:
                for n, line in enumerate(f, 1):
                    m = re.search(r"\bcalls=([^\s]+)", line)
                    if not m:
                        continue
                    for call in m.group(1).split(","):
                        name = re.sub(r"\(.*", "", call).strip()
                        if name and name not in allowed:
                            self.add("WRITE_ACCESS_RECORDED", "run.log:%d" % n, "a call outside the read-only set: %s" % name)
                    if re.search(r"read_only=false", line):
                        self.add("WRITE_ACCESS_RECORDED", "run.log:%d" % n, "a run recorded read_only=false")

    # -- the six files ---------------------------------------------------------
    def load_six(self):
        for name in SIX:
            path = os.path.join(self.d, name)
            if not os.path.exists(path):
                self.add("FILE_MISSING", name, "%s is not present; its rules were not checked" % name)
                self.docs[name] = None
                continue
            doc = self._load(name)
            if doc is None:
                self.docs[name] = None
                continue
            spec = self.files[name]
            self.keys_ok(doc, spec["top"], spec["required"], name, name)
            self.docs[name] = doc

    def check_sources(self):
        doc = self.docs.get("sources.yaml")
        if not doc:
            return
        spec = self.files["sources.yaml"]["entry"]
        for i, s in enumerate(self.list_of_dicts(doc.get("sources"), "sources.yaml", "sources")):
            loc = "sources.yaml sources[%d]" % i
            if not self.keys_ok(s, spec["keys"], spec["required"], loc, loc):
                continue
            if not self.register_id(s.get("id"), "src", loc):
                continue
            sid = s["id"]
            self.sources[sid] = s
            if s.get("kind") not in self.core["source_kinds"]:
                self.add("MALFORMED", sid, "kind %r is not a listed source kind" % s.get("kind"))
            if s.get("environment") not in self.core["environments"]:
                self.add("MALFORMED", sid, "environment %r is not listed" % s.get("environment"))
            if s.get("status") not in self.core["source_status"]:
                self.add("MALFORMED", sid, "status %r is not listed" % s.get("status"))
            acc = s.get("access")
            if not self.keys_ok(acc, spec["access"]["keys"], spec["access"]["required"], sid, sid + " access"):
                continue
            if acc.get("granted") not in self.core["access_granted"] or acc.get("mode") not in self.core["access_modes"]:
                self.add("MALFORMED", sid, "access must be {granted: read_only|none, mode: offline|live}")
                continue
            if acc["mode"] == "live" and acc["granted"] == "read_only":
                au = s.get("authorization")
                aspec = spec["authorization"]
                if not isinstance(au, dict) or any(not au.get(k) for k in aspec["required"]):
                    self.add("LIVE_WITHOUT_AUTHORIZATION", sid, "a live source with read access and no complete authorization {by, at, environment, statement}")
                elif au.get("environment") != s.get("environment"):
                    self.add("LIVE_WITHOUT_AUTHORIZATION", sid, "authorization.environment %r is not the source's environment %r" % (au.get("environment"), s.get("environment")))

    def check_ontology(self):
        doc = self.docs.get("ontology.yaml")
        if not doc:
            return
        spec = self.files["ontology.yaml"]["entry"]
        for i, e in enumerate(self.list_of_dicts(doc.get("entities"), "ontology.yaml", "entities")):
            loc = "ontology.yaml entities[%d]" % i
            if not self.keys_ok(e, spec["keys"], spec["required"], loc, loc):
                continue
            if not self.register_id(e.get("id"), "ent", loc):
                continue
            self.entities[e["id"]] = e
            self.assertion(e, e["id"])
            for j, r in enumerate(self.list_of_dicts(e.get("relationships"), e["id"], "relationships")):
                rl = "%s relationships[%d]" % (e["id"], j)
                for bad in self.core["negative_keys"]:
                    if bad in r:
                        self.add("NEGATIVE_AS_EDGE", rl, "a relationship carries %r; negatives are findings" % bad)
                        r = {k: v for k, v in r.items() if k != bad}
                if not self.keys_ok(r, spec["relationship"]["keys"], spec["relationship"]["required"], rl, rl):
                    continue
                self.assertion(r, rl)

    def check_mappings(self):
        doc = self.docs.get("mappings.yaml")
        if not doc:
            return
        spec = self.files["mappings.yaml"]["entry"]
        for i, m in enumerate(self.list_of_dicts(doc.get("mappings"), "mappings.yaml", "mappings")):
            loc = "mappings.yaml mappings[%d]" % i
            if not self.keys_ok(m, spec["keys"], spec["required"], loc, loc):
                continue
            if not self.register_id(m.get("id"), "map", loc):
                continue
            mid = m["id"]
            self.mappings[mid] = m
            self.assertion(m, mid)
            st = m.get("store")
            self.keys_ok(st, spec["store"]["keys"], spec["store"]["required"], mid, mid + " store")
            for j, f in enumerate(self.list_of_dicts(m.get("fields"), mid, "fields")):
                fl = "%s fields[%d]" % (mid, j)
                if self.keys_ok(f, spec["field"]["keys"], spec["field"]["required"], fl, fl):
                    self.assertion(f, fl)

    def check_lineage(self):
        doc = self.docs.get("lineage.yaml")
        if not doc:
            return
        spec = self.files["lineage.yaml"]
        for i, a in enumerate(self.list_of_dicts(doc.get("activities"), "lineage.yaml", "activities")):
            loc = "lineage.yaml activities[%d]" % i
            if not self.keys_ok(a, spec["activity"]["keys"], spec["activity"]["required"], loc, loc):
                continue
            if not self.register_id(a.get("id"), "act", loc):
                continue
            self.activities[a["id"]] = a
            if a.get("kind") not in self.core["activity_kinds"]:
                self.add("MALFORMED", a["id"], "kind %r is not a listed activity kind" % a.get("kind"))
            if not isinstance(a.get("files"), list) or not a["files"] or any(not isinstance(x, str) or not x for x in a["files"]):
                self.add("ACTIVITY_NO_FILES", a["id"], "an activity cites the files it lives in; drift needs them")
        for i, e in enumerate(self.list_of_dicts(doc.get("edges"), "lineage.yaml", "edges")):
            loc = "lineage.yaml edges[%d]" % i
            if not isinstance(e, dict):
                continue
            if "id" not in e:
                self.add("ID_MISSING", loc, "an edge with no id; run assign_ids.py after Fold")
                continue
            for bad in self.core["negative_keys"]:
                if bad in e:
                    self.add("NEGATIVE_AS_EDGE", str(e.get("id") or loc), "an edge carries %r; negatives are findings" % bad)
                    e = {k: v for k, v in e.items() if k != bad}
            if not self.keys_ok(e, spec["edge"]["keys"], spec["edge"]["required"], loc, loc):
                continue
            if not self.register_id(e.get("id"), "lin", loc):
                continue
            eid = e["id"]
            self.edges[eid] = e
            self.assertion(e, eid)
            rel = e.get("relation")
            if rel not in self.core["prov_relations"]:
                self.add("EDGE_TERM_UNKNOWN", eid, "relation %r is not one of %s" % (rel, self.core["prov_relations"]))
            else:
                et = self.core["edge_types"][rel]
                if _prefix(e.get("subject")) not in et["subject"] or _prefix(e.get("object")) not in et["object"]:
                    self.add("EDGE_TYPE_MISMATCH", eid, "%s needs subject %s and object %s" % (rel, et["subject"], et["object"]))
            rule = e.get("rule")
            if not isinstance(rule, str) or not rule.strip():
                self.add("MALFORMED", eid, "rule must be a non-empty prose string")
            else:
                if any(mk in rule for mk in self.core["code_rule_markers"]):
                    self.add("EDGE_RULE_IS_CODE", eid, "rule reads as code; write the derivation as prose")
                low = rule.strip().lower()
                if any(low.startswith(w) for w in self.core["negative_rule_words"]):
                    self.add("EDGE_READS_NEGATIVE", eid, "rule starts with a negative word; a negative is a finding, not an edge")

    def check_findings(self):
        doc = self.docs.get("findings.yaml")
        if not doc:
            return
        spec = self.files["findings.yaml"]["entry"]
        for i, f in enumerate(self.list_of_dicts(doc.get("findings"), "findings.yaml", "findings")):
            loc = "findings.yaml findings[%d]" % i
            if not isinstance(f, dict):
                continue
            for bad in self.core["edge_shaped_keys"]:
                if bad in f:
                    self.add("FINDING_SHAPED_AS_EDGE", loc, "a finding carries %r; findings have an about list, never ends" % bad)
            if "id" not in f:
                self.add("ID_MISSING", loc, "a finding with no id; run assign_ids.py after Fold")
                continue
            if not self.keys_ok(f, spec["keys"], spec["required"], loc, loc):
                continue
            if not self.register_id(f.get("id"), "fnd", loc):
                continue
            fid = f["id"]
            self.fnds[fid] = f
            self.assertion(f, fid)
            if f.get("kind") not in self.core["finding_kinds"]:
                self.add("MALFORMED", fid, "kind %r is not a listed finding kind" % f.get("kind"))
            if f.get("severity") not in self.core["severities"]:
                self.add("MALFORMED", fid, "severity %r is not high, medium or low" % f.get("severity"))
            st = f.get("status")
            if not (st in ("open", "resolved", "accepted") or (isinstance(st, str) and re.fullmatch(r"ticketed:#\d+", st))):
                self.add("MALFORMED", fid, "status %r is not open, ticketed:#N, resolved or accepted" % (st,))

    def check_questions(self):
        doc = self.docs.get("questions.yaml")
        if not doc:
            return
        spec = self.files["questions.yaml"]["entry"]
        for i, q in enumerate(self.list_of_dicts(doc.get("questions"), "questions.yaml", "questions")):
            loc = "questions.yaml questions[%d]" % i
            if not self.keys_ok(q, spec["keys"], spec["required"], loc, loc):
                continue
            if not self.register_id(q.get("id"), "q", loc):
                continue
            qid = q["id"]
            needs = q.get("needs")
            if not self.keys_ok(needs, spec["needs"]["keys"], [], qid, qid + " needs"):
                continue
            for k in spec["needs"]["keys"]:
                for ident in needs.get(k) or []:
                    if ident not in self.ids:
                        self.add("QUESTION_NEEDS_UNKNOWN", qid, "needs %s, which exists nowhere" % ident)
            if not isinstance(q.get("confirmed_by"), dict):
                self.add("QUESTION_NEEDS_UNCONFIRMED", qid, "the needs list has no confirmed_by; the question counts as not answerable")

    # -- cross-file rules ------------------------------------------------------
    def cross(self):
        # references
        for mid, m in self.mappings.items():
            if m.get("entity") not in self.entities:
                self.add("MAPPING_ENTITY_UNKNOWN", mid, "entity %r is not in the ontology" % m.get("entity"))
            st = m.get("store") or {}
            if isinstance(st, dict) and st.get("source") not in self.sources:
                self.add("SOURCE_UNKNOWN", mid, "store.source %r is not declared in sources.yaml" % st.get("source"))
        for eid, e in self.edges.items():
            for end in ("subject", "object"):
                v = e.get(end)
                if v not in self.ids or _prefix(v) not in ("map", "ent", "act"):
                    self.add("EDGE_ENTITY_UNKNOWN", eid, "%s %r exists nowhere" % (end, v))
        for fid, f in self.fnds.items():
            about = f.get("about")
            if not isinstance(about, list) or not about:
                self.add("MALFORMED", fid, "about must be a non-empty list of IDs")
                continue
            for v in about:
                if v not in self.ids:
                    self.add("FINDING_ABOUT_UNKNOWN", fid, "about %r exists nowhere" % (v,))
        for eid, e in self.entities.items():
            for j, r in enumerate(e.get("relationships") or []):
                if isinstance(r, dict) and r.get("target") not in self.entities:
                    self.add("EDGE_ENTITY_UNKNOWN", "%s relationships[%d]" % (eid, j), "target %r is not in the ontology" % r.get("target"))
        # unextracted sources taint mappings, fields and entities
        unext = {sid for sid, s in self.sources.items() if s.get("status") == "declared-not-extracted"}
        by_entity: dict[str, list] = {}
        for mid, m in self.mappings.items():
            by_entity.setdefault(m.get("entity"), []).append(m)
            src = (m.get("store") or {}).get("source") if isinstance(m.get("store"), dict) else None
            if src in unext:
                if m.get("confidence") != "needs-review":
                    self.add("UNEXTRACTED_SOURCE_NOT_REVIEW", mid, "mapped on %s, declared and not extracted, so it must be needs-review" % src)
                for j, f in enumerate(m.get("fields") or []):
                    if isinstance(f, dict) and f.get("confidence") != "needs-review":
                        self.add("UNEXTRACTED_SOURCE_NOT_REVIEW", "%s fields[%d]" % (mid, j), "a field on an unextracted source must be needs-review")
        for eid, ms in by_entity.items():
            if eid in self.entities and ms and all(
                    isinstance(m.get("store"), dict) and m["store"].get("source") in unext for m in ms):
                if self.entities[eid].get("confidence") != "needs-review":
                    self.add("UNEXTRACTED_SOURCE_NOT_REVIEW", eid, "every mapping of this entity is on an unextracted source, so the entity must be needs-review")
        # ontology names implementation
        store_names: dict[str, set] = {}
        for mid, m in self.mappings.items():
            st = m.get("store") if isinstance(m.get("store"), dict) else {}
            if st.get("name"):
                store_names.setdefault(str(st["name"]).lower(), set()).add(m.get("entity"))
        basenames = set()
        for m in self.mappings.values():
            for k in ("written_by", "read_by"):
                for p in m.get(k) or []:
                    if isinstance(p, str):
                        basenames.add(os.path.basename(p).lower())
        for a in self.activities.values():
            for p in a.get("files") or []:
                if isinstance(p, str):
                    basenames.add(os.path.basename(p).lower())
        for s in self.sources.values():
            for p in s.get("declared_from") or []:
                if isinstance(p, str):
                    basenames.add(os.path.basename(p.split(":")[0]).lower())
        impl_ids = {k.split(":", 1)[1].lower() for k in self.ids if _prefix(k) in ("act", "src")} | {k.lower() for k in self.ids if _prefix(k) in ("act", "src")}
        for eid, e in self.entities.items():
            texts = [("name", e.get("name")), ("definition", e.get("definition"))] + \
                    [("synonym", s) for s in (e.get("synonyms") or [])]
            for label, t in texts:
                if not isinstance(t, str):
                    continue
                if any(mk in t for mk in self.core["implementation_markers"]):
                    self.add("ONTOLOGY_NAMES_IMPLEMENTATION", eid, "%s %r carries a path, URL or file extension" % (label, t))
            tokens = [("name", e.get("name"))] + [("synonym", s) for s in (e.get("synonyms") or [])]
            for label, t in tokens:
                if not isinstance(t, str):
                    continue
                tl = t.strip().lower()
                owners = store_names.get(tl)
                if owners is not None and eid not in owners:
                    self.add("ONTOLOGY_NAMES_IMPLEMENTATION", eid, "%s %r is another entity's store name" % (label, t))
                if tl in impl_ids or tl in basenames:
                    self.add("ONTOLOGY_NAMES_IMPLEMENTATION", eid, "%s %r is an activity, source or file name" % (label, t))

    # -- interpretations --------------------------------------------------------
    def check_interpretations(self):
        root = os.path.join(self.d, "interpretations")
        if not os.path.isdir(root):
            return
        spec = self.files["interpretation"]
        for n in sorted(os.listdir(root)):
            if not n.endswith((".yaml", ".yml")):
                continue
            rel = "interpretations/" + n
            try:
                doc = load_yaml(os.path.join(root, n), self.d)
            except Malformed as e:
                self.add("MALFORMED", rel, "%s: %s" % (rel, e))
                continue
            if not self.keys_ok(doc, spec["top"], spec["required"], rel, rel):
                continue
            inputs = doc.get("inputs")
            if not isinstance(inputs, list) or any(not isinstance(x, str) for x in inputs):
                self.add("MALFORMED", rel, "inputs must be a list of paths")
                continue
            prop = doc.get("proposed")
            if not self.keys_ok(prop, spec["proposed"]["keys"], [], rel, rel + " proposed"):
                continue
            ont = prop.get("ontology")
            if isinstance(ont, dict) and ont:
                self.assertion(ont, rel + " ontology", in_four=False, inputs=inputs, model_written=True)
                for j, r in enumerate(ont.get("relationships") or []):
                    if isinstance(r, dict):
                        self.assertion(r, "%s ontology relationships[%d]" % (rel, j), in_four=False, inputs=inputs, model_written=True)
            for j, m in enumerate(self.list_of_dicts(prop.get("mappings"), rel, rel + " mappings")):
                self.assertion(m, "%s mappings[%d]" % (rel, j), in_four=False, inputs=inputs, model_written=True)
                for k, f in enumerate(m.get("fields") or []):
                    if isinstance(f, dict):
                        self.assertion(f, "%s mappings[%d] fields[%d]" % (rel, j, k), in_four=False, inputs=inputs, model_written=True)
            lin = prop.get("lineage") or {}
            if isinstance(lin, dict):
                for j, e in enumerate(self.list_of_dicts(lin.get("edges"), rel, rel + " edges")):
                    el = "%s edges[%d]" % (rel, j)
                    if "id" in e:
                        self.add("ID_PROPOSED_BY_MODEL", el, "an interpretation edge carries an id; assign_ids.py numbers edges after Fold")
                    self.assertion(e, el, in_four=False, inputs=inputs, model_written=True)
            for j, f in enumerate(self.list_of_dicts(prop.get("findings"), rel, rel + " findings")):
                fl = "%s findings[%d]" % (rel, j)
                if "id" in f:
                    self.add("ID_PROPOSED_BY_MODEL", fl, "an interpretation finding carries an id; assign_ids.py numbers findings after Fold")
                self.assertion(f, fl, in_four=False, inputs=inputs, model_written=True)

    # -- manifest ---------------------------------------------------------------
    def check_manifest(self):
        if not self.manifest_path or not os.path.exists(self.manifest_path):
            return
        try:
            man = load_yaml(self.manifest_path, os.path.dirname(os.path.abspath(self.manifest_path)))
        except Malformed as e:
            self.add("MALFORMED", self.manifest_path, "manifest: %s" % e)
            return
        names = set()
        for e in self.entities.values():
            if isinstance(e.get("name"), str):
                names.add(e["name"].strip().lower())
            for s in e.get("synonyms") or []:
                if isinstance(s, str):
                    names.add(s.strip().lower())
        domains = man.get("domains")
        if not isinstance(domains, dict):
            return
        for dname, dom in domains.items():
            be = (dom or {}).get("boundary_entities") if isinstance(dom, dict) else None
            if not isinstance(be, dict):
                continue
            for bname in be:
                if str(bname).strip().lower() not in names:
                    self.add("BOUNDARY_NOT_IN_ONTOLOGY", kebab(bname), "manifest domain %s names boundary entity %r; no ontology entity or synonym matches" % (dname, bname))

    # -- waivers ----------------------------------------------------------------
    def apply_waivers(self):
        if not self.waivers_path or not os.path.exists(self.waivers_path):
            return
        try:
            doc = load_yaml(self.waivers_path, os.path.dirname(os.path.abspath(self.waivers_path)))
        except Malformed as e:
            self.add("MALFORMED", self.waivers_path, "waiver file: %s" % e)
            return
        rows = doc.get("waivers") or []
        if not isinstance(rows, list):
            self.add("MALFORMED", self.waivers_path, "waivers must be a list")
            return
        live = {}
        for r in rows:
            if not isinstance(r, dict):
                continue
            code, locus = r.get("code"), r.get("locus")
            if code not in WAIVER_ELIGIBLE or not isinstance(locus, str) or locus != kebab(locus):
                continue
            try:
                revisit = r.get("revisit")
                if isinstance(revisit, str):
                    revisit = dt.date.fromisoformat(revisit)
                if not isinstance(revisit, dt.date) or revisit < self.today:
                    continue
                if int(r.get("tier_limit", -1)) < self.tier:
                    continue
            except (TypeError, ValueError):
                continue
            if not r.get("owner") or not r.get("reason"):
                continue
            live[(code, locus)] = r
        for f in self.findings:
            if f["waivable"] and (f["code"], f["locus"]) in live:
                f["waived"] = True
                f["message"] += " (waived by %s: %s)" % (live[(f["code"], f["locus"])]["owner"], live[(f["code"], f["locus"])]["reason"])

    # -- run ----------------------------------------------------------------------
    def run(self) -> list[dict]:
        self.load_evidence()
        self.load_six()
        self.check_sources()
        self.check_ontology()
        self.check_mappings()
        self.check_lineage()
        self.check_findings()
        self.check_questions()
        self.cross()
        self.check_interpretations()
        self.check_manifest()
        self.apply_waivers()
        return self.findings


def run(data_dir: str, schema_path: str, manifest: str | None, waivers: str | None,
        tier: int = 3, today: dt.date | None = None) -> tuple[list[dict], int, str]:
    """Returns (findings, exit_code, absent_note). Never raises on hostile input."""
    if not os.path.isdir(data_dir):
        return [], 0, "data layer: absent (%s)" % data_dir
    try:
        schema = load_yaml(schema_path, os.path.dirname(os.path.abspath(schema_path)))
        if "core" not in schema or "files" not in schema:
            raise Malformed("schema has no core/files")
    except Malformed as e:
        return [{"code": "MALFORMED", "locus": schema_path, "message": "schema: %s" % e, "waivable": False}], 2, ""
    try:
        findings = Checker(data_dir, schema, manifest, waivers, tier, today).run()
    except Exception as e:  # the last line of defence: fail closed, never a traceback
        findings = [{"code": "MALFORMED", "locus": data_dir, "message": "validator could not finish: %s: %s" % (e.__class__.__name__, e), "waivable": False}]
    blockers = [f for f in findings if not f["waivable"]]
    warnings = [f for f in findings if f["waivable"] and not f.get("waived")]
    return findings, (2 if blockers else 0), "" if not warnings else "warnings"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", default="docs/02-design/data")
    ap.add_argument("--manifest", default="docs/system-manifest.yaml")
    ap.add_argument("--schema", default=os.path.join(HERE, "data-layer.schema.yaml"))
    ap.add_argument("--waivers", default=os.path.join(HERE, "data-layer-waivers.yaml"))
    ap.add_argument("--tier", type=int, default=3)
    ap.add_argument("--strict", action="store_true", help="exit 1 on an unwaived warning")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    findings, code, note = run(a.data_dir, a.schema, a.manifest, a.waivers, a.tier)
    if note.startswith("data layer: absent"):
        print(note)
        return 0
    if a.json:
        print(json.dumps(findings, indent=2))
    else:
        for f in sorted(findings, key=lambda f: (f["waivable"], f["code"], f["locus"])):
            tag = "waived" if f.get("waived") else ("warn" if f["waivable"] else "BLOCK")
            print("%-6s %-32s %s: %s" % (tag, f["code"], f["locus"], f["message"]))
        b = sum(1 for f in findings if not f["waivable"])
        w = sum(1 for f in findings if f["waivable"] and not f.get("waived"))
        print("data layer: %d blocking, %d warning%s" % (b, w, "" if w == 1 else "s"))
    if code == 0 and a.strict and any(f["waivable"] and not f.get("waived") for f in findings):
        return 1
    return code


if __name__ == "__main__":
    sys.exit(main())
