#!/usr/bin/env python3
"""The reasoning stage (FR-31, DL-21, DL-22; ADR-14, ADR-17).

Loads the compiled ontology, shapes and rules by confidence, runs the checks, and writes what it
found as evidence and proposed findings. Nothing here edits the four files; a person or the fold
promotes what it proposes.

Two runs:
  strict        loads assertions at `confirmed` only; findings may block at the Depended-on level
  exploratory   loads `confirmed` and `inferred`; findings are advisory
An assertion at `needs-review` is never loaded, and a request to include one is refused (exit 2).

Checks, always (pure Python): the OWL 2 RL closure (owlrl) over the ontology plus instance data,
then SHACL validation and SHACL-AF rules (pySHACL). When a JVM and Owlready2 are present, HermiT
runs the full OWL 2 DL consistency and classification; otherwise that check is recorded as not run.

Instances (DL-22): rows from offline exports, one JSONL per store, converted to RDF through the
mappings (field -> property, natural key -> instance IRI). Pass --instances <store>=<path> or let
the script find exports/<store>.jsonl under --root.

Writes:
  evidence/reasoning/inference-<ts>.yaml   evidence type `inference`, one item per result
  compiled/reasoning-run.yaml              what was loaded, which checks ran, counts
  compiled/reasoning-findings.yaml         findings at `inferred` citing the evidence items, with no ids

Optional dependencies: rdflib, owlrl, pyshacl. Without them: one SKIPPED line, exit 0.

    python3 tools/data-layer/reason.py --data-dir docs/02-design/data --mode strict|exploratory
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from dl_common import dump_yaml, envelope, file_stamp, load_yaml, now_utc, stamp  # noqa: E402

try:
    from rdflib import BNode, Graph, Literal, Namespace, URIRef
    from rdflib.namespace import OWL, RDF, RDFS, SH, XSD
    HAVE_RDFLIB = True
except ImportError:  # pragma: no cover
    HAVE_RDFLIB = False
try:
    import owlrl
    HAVE_OWLRL = True
except ImportError:  # pragma: no cover
    HAVE_OWLRL = False
try:
    import pyshacl
    HAVE_PYSHACL = True
except ImportError:  # pragma: no cover
    HAVE_PYSHACL = False

VERSION = "1.1.0"
HITL = "https://hitl.dev/ns/data-layer#"
ORDER = {"confirmed": 0, "inferred": 1, "needs-review": 2}
MODES = {"strict": {"confirmed"}, "exploratory": {"confirmed", "inferred"}}


def local(ident: str) -> str:
    prefix, _, rest = ident.partition(":")
    rest = re.sub(r"[^A-Za-z0-9_.\-]", ".", rest)
    return rest if prefix == "ent" else "%s.%s" % (prefix, rest)


class Reasoner:
    def __init__(self, data_dir: str, mode: str, root: str):
        self.d = data_dir
        self.mode = mode
        self.root = root
        self.allowed = MODES[mode]
        self.H = Namespace(HITL)
        self.loaded = {"confirmed": 0, "inferred": 0, "needs-review": 0}   # actually loaded
        self.seen = {"confirmed": 0, "inferred": 0, "needs-review": 0}     # present in the compiled files
        self.dropped: list[str] = []
        self.results: list[dict] = []     # {kind, locator, data}
        self.checks: dict[str, str] = {}  # name -> ran | not-run: reason
        self.base = None

    # -- loading by confidence ----------------------------------------------
    def load_filtered(self, path: str) -> Graph:
        """Keep a node's triples only when its hitl:confidence is allowed. A node with no confidence
        (vocabulary, prefixes, the ontology header) is kept. Axiom annotations gate the annotated
        triple too."""
        g = Graph()
        g.parse(path, format="turtle")
        keep = Graph()
        for p, ns in g.namespaces():
            keep.bind(p, ns)
        drop_nodes = set()
        for s, _, c in g.triples((None, self.H.confidence, None)):
            conf = str(c)
            self.seen[conf] = self.seen.get(conf, 0) + 1
            if conf not in self.allowed:
                drop_nodes.add(s)
            else:
                self.loaded[conf] = self.loaded.get(conf, 0) + 1
        # an annotated axiom: drop the reified triple when its annotation is dropped
        dropped_triples = set()
        for ax in list(drop_nodes):
            if (ax, RDF.type, OWL.Axiom) in g:
                src = g.value(ax, OWL.annotatedSource)
                prp = g.value(ax, OWL.annotatedProperty)
                tgt = g.value(ax, OWL.annotatedTarget)
                dropped_triples.add((src, prp, tgt))
        for s, p, o in g:
            if s in drop_nodes or o in drop_nodes or (s, p, o) in dropped_triples:
                continue
            keep.add((s, p, o))
        # prune bnodes that became orphans (restrictions whose subclass axiom was dropped)
        changed = True
        while changed:
            changed = False
            for s in set(keep.subjects()):
                if isinstance(s, BNode) and not list(keep.triples((None, None, s))) and (s, RDF.type, OWL.Axiom) not in keep:
                    for t in list(keep.triples((s, None, None))):
                        keep.remove(t)
                    changed = True
        for n in drop_nodes:
            self.dropped.append(str(n))
        return keep

    # -- instances --------------------------------------------------------------
    def load_instances(self, specs: dict[str, str]) -> Graph:
        g = Graph()
        mdoc = load_yaml(os.path.join(self.d, "mappings.yaml"))
        NS = Namespace(self.base)
        for m in mdoc.get("mappings") or []:
            if not isinstance(m, dict):
                continue
            conf = m.get("confidence")
            if conf not in self.allowed:
                continue
            store = (m.get("store") or {}).get("name")
            path = specs.get(store) or self.find_export(store)
            if not path:
                self.checks["instances:%s" % store] = "not-run: no export found"
                continue
            eid = m["entity"]
            cls = NS[local(eid)]
            fields = {f["name"]: f for f in (m.get("fields") or []) if isinstance(f, dict) and f.get("name")}
            n = 0
            with open(path, encoding="utf-8") as f:
                for i, line in enumerate(f):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        row = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    # one node per row, never per key value: two rows that share a natural key are a
                    # duplicate the key check must see, not one individual (DL-22)
                    node = NS["%s/%s-%d" % (local(eid), re.sub(r"[^A-Za-z0-9_]", "_", str(store)), i + 1)]
                    g.add((node, RDF.type, cls))
                    g.add((node, self.H.fromStore, Literal("%s:%d" % (store, i + 1))))
                    for fname, val in row.items():
                        if fname not in fields or val is None:
                            continue
                        prop = NS["%s.%s" % (local(eid), re.sub(r"[^A-Za-z0-9_]", "_", fname))]
                        g.add((node, prop, self.literal(val, fields[fname].get("type"))))
                    n += 1
            self.checks["instances:%s" % store] = "ran: %d rows from %s" % (n, os.path.relpath(path, self.root))
        return g

    def find_export(self, store: str) -> str | None:
        for cand in (os.path.join(self.root, "exports", "%s.jsonl" % store),
                     os.path.join(self.d, "..", "..", "..", "exports", "%s.jsonl" % store)):
            if os.path.isfile(cand):
                return os.path.abspath(cand)
        return None

    @staticmethod
    def literal(val, ftype):
        t = str(ftype or "").lower()
        if val == "":
            return Literal("")
        try:
            if t in ("integer", "int", "bigint", "smallint"):
                return Literal(int(val), datatype=XSD.integer)
            if t in ("date",):
                return Literal(str(val), datatype=XSD.date)
            if t in ("timestamp", "datetime", "timestamptz"):
                return Literal(str(val).replace("Z", "+00:00"), datatype=XSD.dateTime)
            if t in ("boolean", "bool"):
                return Literal(bool(val))
            if t in ("number", "numeric", "decimal", "float", "double"):
                return Literal(float(val), datatype=XSD.decimal)
        except (TypeError, ValueError):
            pass
        return Literal(str(val))

    # -- checks -------------------------------------------------------------------
    def owl_rl(self, data: Graph, onto: Graph) -> Graph:
        if not HAVE_OWLRL:
            self.checks["owl-rl"] = "not-run: owlrl not installed"
            return data
        g = Graph()
        # owl:hasKey is kept out of the closure on purpose: in instance data a shared natural key is a
        # duplicate row, a finding, never two names for one individual. Keys are checked by key_check.
        keys = self.collect_keys(onto)
        key_lists = {lst for _, lst in onto.subject_objects(OWL.hasKey)}
        list_nodes = set()
        for lst in key_lists:
            node = lst
            while node and node != RDF.nil:
                list_nodes.add(node)
                node = onto.value(node, RDF.rest)
        for s, p, o in onto:
            if p == OWL.hasKey or s in list_nodes:
                continue
            g.add((s, p, o))
        for t in data:
            g.add(t)
        before = len(g)
        owlrl.DeductiveClosure(owlrl.OWLRL_Semantics, axiomatic_triples=False, datatype_axioms=False).expand(g)
        self.checks["owl-rl"] = "ran: %d triples before, %d after" % (before, len(g))
        self.key_check(g, keys)
        # inconsistency under OWL 2 RL: an individual typed owl:Nothing, or owlrl's own error marker
        err_ns = "http://www.daml.org/2002/03/agents/agent-ont#"
        for s in set(g.subjects(RDF.type, OWL.Nothing)):
            if s == OWL.Nothing:
                continue
            kind = "unsatisfiable" if (s, RDF.type, OWL.Class) in g else "inconsistency"
            self.results.append({"kind": kind, "locator": str(s), "data": {"check": "owl-rl", "reason": "typed owl:Nothing after the OWL 2 RL closure"}})
        for s, p, o in g:
            if str(p).startswith(err_ns) or str(o).startswith(err_ns):
                self.results.append({"kind": "inconsistency", "locator": str(s), "data": {"check": "owl-rl", "reason": str(o)}})
        # inferred class memberships and subclass axioms that were not stated
        for s, o in g.subject_objects(RDFS.subClassOf):
            if isinstance(s, URIRef) and isinstance(o, URIRef) and s != o and o not in (OWL.Thing, RDFS.Resource) \
                    and (s, RDFS.subClassOf, o) not in onto and str(s).startswith(self.base) and str(o).startswith(self.base):
                self.results.append({"kind": "inferred-axiom", "locator": "%s subClassOf %s" % (s, o), "data": {"check": "owl-rl"}})
        return g

    def collect_keys(self, onto: Graph) -> dict:
        keys: dict = {}
        for cls, lst in onto.subject_objects(OWL.hasKey):
            props = []
            node = lst
            while node and node != RDF.nil:
                p = onto.value(node, RDF.first)
                if p is not None:
                    props.append(p)
                node = onto.value(node, RDF.rest)
            if props:
                keys.setdefault(cls, []).append(tuple(props))
        return keys

    def key_check(self, g: Graph, keys: dict):
        """Two instances of a class with the same values on every key property are a duplicate (DL-22)."""
        n = 0
        for cls, key_sets in keys.items():
            inst = list(g.subjects(RDF.type, cls))
            for props in key_sets:
                seen: dict = {}
                for x in inst:
                    vals = tuple(g.value(x, p) for p in props)
                    if any(v is None for v in vals):
                        continue
                    seen.setdefault(vals, []).append(x)
                for vals, xs in seen.items():
                    if len(xs) > 1:
                        n += 1
                        self.results.append({"kind": "violation", "locator": " ".join(str(x) for x in xs[:4]),
                                             "data": {"check": "keys", "message": "%d instances of %s share the key %s" % (len(xs), cls, [str(v) for v in vals]),
                                                      "component": "KeyConstraint", "shape": str(cls)}})
        self.checks["keys"] = "ran: %d duplicate key group%s" % (n, "" if n == 1 else "s")

    def shacl(self, data: Graph, shapes: Graph, rules: Graph, label: str):
        if not HAVE_PYSHACL:
            self.checks["shacl"] = "not-run: pyshacl not installed"
            return
        sg = Graph()
        for t in shapes:
            sg.add(t)
        for t in rules:
            sg.add(t)
        conforms, report, _ = pyshacl.validate(data, shacl_graph=sg, advanced=True, inference="none",
                                               allow_warnings=True, iterate_rules=True)
        n = 0
        for r in report.subjects(RDF.type, SH.ValidationResult):
            n += 1
            focus = report.value(r, SH.focusNode)
            path = report.value(r, SH.resultPath)
            msg = report.value(r, SH.resultMessage)
            src = report.value(r, SH.sourceShape)
            comp = report.value(r, SH.sourceConstraintComponent)
            self.results.append({"kind": "violation", "locator": "%s %s" % (focus, path or ""),
                                 "data": {"check": "shacl", "message": str(msg), "shape": str(src),
                                          "component": str(comp).split("#")[-1], "graph": label}})
        self.checks["shacl"] = "ran: %s, %d result%s" % ("conforms" if conforms else "violations", n, "" if n == 1 else "s")

    def fire_rules(self, data: Graph, rules: Graph) -> dict:
        """Run each SHACL-AF rule by hand so the run record can say what every rule derived. pySHACL
        applies the rules during validation but keeps the derived triples to itself."""
        fired: dict[str, int] = {}
        for shape in rules.subjects(RDF.type, SH.NodeShape):
            rid = str(rules.value(shape, self.H.id) or shape)
            cls = rules.value(shape, SH.targetClass)
            if cls is None:
                continue
            focus = list(data.subjects(RDF.type, cls))
            for rule in rules.objects(shape, SH.rule):
                cond = rules.value(rule, SH.condition)
                cond_q = None
                if cond is not None:
                    c = rules.value(cond, SH.sparql)
                    cond_q = str(rules.value(c, SH.select)) if c is not None else None
                n = 0
                for f in focus:
                    if cond_q:
                        q = cond_q.replace("$this", "?this")
                        if not list(data.query(q, initBindings={"this": f})):
                            continue
                    if (rule, RDF.type, SH.SPARQLRule) in rules:
                        q = str(rules.value(rule, SH.construct)).replace("$this", "?this")
                        for t in data.query(q, initBindings={"this": f}):
                            if t not in data:
                                data.add(t)
                                n += 1
                    elif (rule, RDF.type, SH.TripleRule) in rules:
                        p = rules.value(rule, SH.predicate)
                        o = rules.value(rule, SH.object)
                        if (f, p, o) not in data:
                            data.add((f, p, o))
                            n += 1
                fired[rid] = fired.get(rid, 0) + n
        self.checks["rules"] = "ran: %s" % (", ".join("%s derived %d" % (k, v) for k, v in fired.items()) or "no rules loaded")
        return fired

    def hermit(self, onto_path: str):
        try:
            import owlready2  # noqa: F401
        except ImportError:
            self.checks["hermit"] = "not-run: owlready2 not installed"
            return
        if not shutil.which("java"):
            self.checks["hermit"] = "not-run: no JVM on PATH"
            return
        try:
            import owlready2
            import tempfile
            # Owlready2 reads RDF/XML, OWL/XML or N-Triples, never Turtle: convert first
            g = Graph().parse(onto_path, format="turtle")
            tmp = tempfile.NamedTemporaryFile(suffix=".owl", delete=False)
            tmp.close()
            g.serialize(destination=tmp.name, format="xml")
            world = owlready2.World()
            onto = world.get_ontology("file://" + tmp.name).load()
            with onto:
                owlready2.sync_reasoner_hermit(world, infer_property_values=False, debug=0)
            bad = list(world.inconsistent_classes())
            for c in bad:
                self.results.append({"kind": "unsatisfiable", "locator": str(c.iri), "data": {"check": "hermit"}})
            self.checks["hermit"] = "ran: %d unsatisfiable class%s" % (len(bad), "" if len(bad) == 1 else "es")
        except Exception as e:  # a reasoner crash is recorded, never raised
            self.checks["hermit"] = "not-run: %s: %s" % (e.__class__.__name__, str(e)[:120])

    # -- run ------------------------------------------------------------------------
    def run(self, instances: dict[str, str], with_hermit: bool) -> tuple[dict, list[dict]]:
        comp = os.path.join(self.d, "compiled")
        pin = load_yaml(os.path.join(comp, "pin.yaml"))
        if not pin:
            raise SystemExit("ERROR: no compiled/pin.yaml; run compile_ontology.py first")
        self.base = pin.get("base_iri")
        onto = self.load_filtered(os.path.join(comp, "ontology.ttl"))
        shapes = self.load_filtered(os.path.join(comp, "shapes.ttl"))
        rules = self.load_filtered(os.path.join(comp, "rules.ttl"))
        data = self.load_instances(instances)
        closed = self.owl_rl(data, onto)
        fired = self.fire_rules(closed, rules)
        self.shacl(closed, shapes, rules, "ontology+instances after OWL RL and rules")
        if with_hermit:
            self.hermit(os.path.join(comp, "ontology.ttl"))
        else:
            self.checks["hermit"] = "not-run: not requested"
        ts = now_utc()
        # evidence: one file, one item per result
        items = [{"kind": r["kind"], "locator": r["locator"], "data": r["data"]} for r in self.results]
        ev = envelope("inference", "src:reasoning", ts, "reason.py",
                      {"mode": "offline", "environment": "offline-export", "read_only": True}, items,
                      extra={"coverage": {"mode": self.mode, "loaded": self.loaded, "seen": self.seen, "checks": self.checks}})
        ev_rel = "evidence/reasoning/inference-%s.yaml" % file_stamp(ts)
        dump_yaml(os.path.join(self.d, ev_rel), ev)
        # proposed findings, no ids (assign_ids.py numbers them at fold)
        sev = {"inconsistency": "high", "unsatisfiable": "high", "violation": "medium", "inferred-axiom": "low"}
        findings = []
        for i, r in enumerate(self.results):
            about = [a for a in self.about(r)]
            findings.append({"kind": r["kind"], "severity": sev[r["kind"]], "about": about or ["ent:unknown"],
                             "statement": self.statement(r), "confidence": "inferred",
                             "evidence": [{"file": ev_rel, "item": ev["items"][i]["id"]}], "status": "open",
                             "written_at": stamp(ts)})
        run = {"schema_version": "1.1", "run_at": stamp(ts), "mode": self.mode, "loaded": self.loaded, "seen": self.seen,
               "dropped": len(self.dropped), "checks": self.checks, "pin": pin.get("compiled_at"), "rules_fired": fired,
               "results": {k: sum(1 for r in self.results if r["kind"] == k) for k in sev}}
        dump_yaml(os.path.join(comp, "reasoning-run.yaml"), run)
        dump_yaml(os.path.join(comp, "reasoning-findings.yaml"), {"schema_version": "1.1", "findings": findings})
        with open(os.path.join(self.d, "run.log"), "a", encoding="utf-8") as f:
            f.write("%s reason.py mode=%s loaded=%s read_only=true results=%d\n" % (stamp(ts), self.mode, json.dumps(self.loaded), len(self.results)))
        return run, findings

    def about(self, r: dict) -> list[str]:
        """Map an IRI back to a YAML id where the local name allows it."""
        out = []
        for tok in re.findall(r"[A-Za-z0-9_.\-/]+", r["locator"]):
            tok = tok.split("#")[-1]
            m = re.match(r"^([a-z0-9\-]+)(?:/|\.|$)", tok)
            if m and self.base and tok and not tok.startswith(("http", "www")):
                ent = "ent:" + m.group(1)
                if ent not in out and re.match(r"^[a-z][a-z0-9\-]*$", m.group(1)):
                    out.append(ent)
        return out[:3]

    @staticmethod
    def statement(r: dict) -> str:
        d = r["data"]
        if r["kind"] == "violation":
            return "%s (%s) on %s" % (d.get("message"), d.get("component"), r["locator"])
        if r["kind"] == "inferred-axiom":
            return "The reasoner infers %s, which the ontology does not state." % r["locator"]
        return "%s: %s (%s)" % (r["kind"], r["locator"], d.get("reason", d.get("check")))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", default="docs/02-design/data")
    ap.add_argument("--root", default=".", help="repo root; exports/<store>.jsonl are found under it")
    ap.add_argument("--mode", choices=["strict", "exploratory"], default="strict")
    ap.add_argument("--include-needs-review", action="store_true", help="refused (ADR-17)")
    ap.add_argument("--instances", action="append", default=[], metavar="STORE=PATH")
    ap.add_argument("--hermit", action="store_true", help="also run HermiT when a JVM is present")
    a = ap.parse_args(argv)
    if a.include_needs_review:
        print("REFUSED: a reasoning run never loads a needs-review assertion (DL-21, ADR-17)")
        return 2
    if not (HAVE_RDFLIB and HAVE_OWLRL and HAVE_PYSHACL):
        print("SKIPPED: reasoning needs rdflib, owlrl and pyshacl (pip install rdflib owlrl pyshacl); not run.")
        return 0
    if not os.path.isdir(a.data_dir):
        print("data layer: absent (%s)" % a.data_dir)
        return 0
    specs = dict(s.split("=", 1) for s in a.instances if "=" in s)
    r = Reasoner(a.data_dir, a.mode, a.root)
    run, findings = r.run(specs, a.hermit)
    print("reasoning (%s): loaded %s, dropped %d" % (run["mode"], run["loaded"], run["dropped"]))
    for k, v in run["checks"].items():
        print("  %-22s %s" % (k, v))
    print("results: %s" % ", ".join("%s %d" % (k, v) for k, v in run["results"].items()))
    for f in findings[:12]:
        print("  [%s/%s] %s" % (f["kind"], f["severity"], f["statement"][:150]))
    if len(findings) > 12:
        print("  ... %d more in compiled/reasoning-findings.yaml" % (len(findings) - 12))
    return 0


if __name__ == "__main__":
    sys.exit(main())
