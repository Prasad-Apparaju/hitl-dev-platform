#!/usr/bin/env python3
"""Compile the data layer's YAML into a formal ontology (FR-31, DL-20; ADR-16).

Reads docs/02-design/data/{ontology,mappings,lineage,rules,actions}.yaml and writes, under
docs/02-design/data/compiled/:

  ontology.ttl   OWL 2: one class per entity, one object property per relationship, axioms (DL-18),
                 owl:hasKey from every mapping's natural key, the decision-trace module (DL-23)
  shapes.ttl     SHACL: one node shape per entity with a property shape per mapped field and per
                 relationship; Action Catalog pre- and postconditions when actions.yaml exists (DL-29)
  rules.ttl      SHACL-AF rules from rules.yaml (DL-19)
  pin.yaml       the sha256 of every input, so the validator can tell a stale compile (DL-20)

Every assertion carries hitl:confidence, hitl:evidence, hitl:confirmedBy and hitl:writtenAt as
annotation properties, so the reasoning stage can load by confidence (ADR-17). The YAML is the only
source of truth; these files are outputs and are never edited by hand.

Optional dependency: rdflib. Without it the script prints one SKIPPED line and exits 0 (NFR-1).

    python3 tools/data-layer/compile_ontology.py --data-dir docs/02-design/data [--base IRI]
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import os
import re
import sys

try:
    import yaml
except ImportError:  # pragma: no cover
    print("ERROR: pyyaml required. Run: pip install pyyaml")
    sys.exit(2)

try:
    from rdflib import BNode, Graph, Literal, Namespace, URIRef
    from rdflib.collection import Collection
    from rdflib.namespace import OWL, RDF, RDFS, SH, SKOS, XSD
    HAVE_RDFLIB = True
except ImportError:  # pragma: no cover
    HAVE_RDFLIB = False

VERSION = "1.1.0"
HITL = "https://hitl.dev/ns/data-layer#"
DT = "https://hitl.dev/ns/decision-trace#"
PROV = "http://www.w3.org/ns/prov#"
DEFAULT_BASE = "https://hitl.dev/ns/system#"

FOUR = ("ontology.yaml", "mappings.yaml", "lineage.yaml", "findings.yaml")
OPTIONAL = ("rules.yaml", "actions.yaml")

TYPE_MAP = {
    "integer": "integer", "int": "integer", "bigint": "integer", "smallint": "integer",
    "text": "string", "string": "string", "varchar": "string", "char": "string", "uuid": "string",
    "date": "date", "timestamp": "dateTime", "datetime": "dateTime", "timestamptz": "dateTime",
    "boolean": "boolean", "bool": "boolean",
    "number": "decimal", "numeric": "decimal", "decimal": "decimal", "float": "decimal", "double": "decimal",
    "json": None, "jsonb": None, "array": None, "object": None,
}


def load(path: str) -> dict | None:
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        d = yaml.safe_load(f)
    return d if isinstance(d, dict) else {}


def sha(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def local(ident: str) -> str:
    """ent:order-line -> order-line ; map:order/orders-db.orders -> map.order.orders-db.orders"""
    prefix, _, rest = ident.partition(":")
    rest = re.sub(r"[^A-Za-z0-9_.\-]", ".", rest)
    return rest if prefix == "ent" else "%s.%s" % (prefix, rest)


class Compiler:
    def __init__(self, data_dir: str, base: str, decision_trace: bool):
        self.d = data_dir
        self.base = base if base.endswith(("#", "/")) else base + "#"
        self.decision_trace = decision_trace
        self.NS = Namespace(self.base)
        self.H = Namespace(HITL)
        self.DTN = Namespace(DT)
        self.P = Namespace(PROV)
        self.onto = Graph()
        self.shapes = Graph()
        self.rules = Graph()
        for g in (self.onto, self.shapes, self.rules):
            g.bind("", self.NS)
            g.bind("hitl", self.H)
            g.bind("dt", self.DTN)
            g.bind("prov", self.P)
            g.bind("owl", OWL)
            g.bind("sh", SH)
            g.bind("skos", SKOS)
            g.bind("xsd", XSD)
        self.docs: dict[str, dict | None] = {}
        self.entities: dict[str, dict] = {}
        self.entity_iri: dict[str, URIRef] = {}
        self.prop_iri: dict[tuple[str, str], URIRef] = {}
        self.notes: list[str] = []

    # -- annotations ---------------------------------------------------------
    def annotate(self, g: Graph, node, obj: dict, yaml_id: str | None = None):
        g.add((node, self.H.confidence, Literal(obj.get("confidence", "needs-review"))))
        for ref in obj.get("evidence") or []:
            if isinstance(ref, dict):
                g.add((node, self.H.evidence, Literal("%s#%s" % (ref.get("file"), ref.get("item")))))
        cb = obj.get("confirmed_by")
        if isinstance(cb, dict) and cb.get("who"):
            g.add((node, self.H.confirmedBy, Literal("%s %s %s" % (cb.get("how"), cb.get("who"), cb.get("at")))))
        if obj.get("written_at"):
            g.add((node, self.H.writtenAt, Literal(str(obj["written_at"]), datatype=XSD.dateTime)))
        if yaml_id:
            g.add((node, self.H.id, Literal(yaml_id)))

    def annotated_axiom(self, g: Graph, s, p, o, obj: dict):
        """An OWL axiom annotation: the triple plus a reified owl:Axiom carrying confidence and evidence."""
        g.add((s, p, o))
        ax = BNode()
        g.add((ax, RDF.type, OWL.Axiom))
        g.add((ax, OWL.annotatedSource, s))
        g.add((ax, OWL.annotatedProperty, p))
        g.add((ax, OWL.annotatedTarget, o))
        self.annotate(g, ax, obj)

    # -- ontology --------------------------------------------------------------
    def entity_node(self, ident: str) -> URIRef:
        if ident not in self.entity_iri:
            self.entity_iri[ident] = self.NS[local(ident)]
        return self.entity_iri[ident]

    def compile_ontology(self):
        g = self.onto
        ont = URIRef(self.base.rstrip("#/"))
        g.add((ont, RDF.type, OWL.Ontology))
        g.add((ont, RDFS.comment, Literal("Compiled by HITL compile_ontology.py %s from the data layer YAML; do not edit." % VERSION)))
        for p, label in (("confidence", "confidence of the assertion: confirmed, inferred or needs-review"),
                         ("evidence", "an evidence reference file#item"), ("confirmedBy", "how who at"),
                         ("writtenAt", "when the assertion was written"), ("id", "the YAML id")):
            g.add((self.H[p], RDF.type, OWL.AnnotationProperty))
            g.add((self.H[p], RDFS.label, Literal(label)))
        doc = self.docs.get("ontology.yaml") or {}
        for e in doc.get("entities") or []:
            if not isinstance(e, dict) or not e.get("id"):
                continue
            self.entities[e["id"]] = e
            c = self.entity_node(e["id"])
            g.add((c, RDF.type, OWL.Class))
            g.add((c, RDFS.label, Literal(e.get("name", e["id"]))))
            if e.get("definition"):
                g.add((c, RDFS.comment, Literal(e["definition"])))
            for syn in e.get("synonyms") or []:
                g.add((c, SKOS.altLabel, Literal(str(syn))))
            self.annotate(g, c, e, e["id"])
        # relationships and axioms need every class first
        for eid, e in self.entities.items():
            c = self.entity_node(eid)
            for r in e.get("relationships") or []:
                if not isinstance(r, dict) or not r.get("name") or not r.get("target"):
                    continue
                self.compile_relationship(c, eid, r)
            for a in e.get("axioms") or []:
                if isinstance(a, dict):
                    self.compile_axiom(c, eid, a)
        # keys from mappings (DL-18): each mapping's natural key becomes an owl:hasKey on the entity
        mdoc = self.docs.get("mappings.yaml") or {}
        for m in mdoc.get("mappings") or []:
            if not isinstance(m, dict) or not m.get("entity") or not m.get("natural_key"):
                continue
            if m["entity"] not in self.entities:
                continue
            c = self.entity_node(m["entity"])
            props = [self.field_prop(m["entity"], f) for f in m["natural_key"]]
            lst = BNode()
            Collection(g, lst, props)
            self.annotated_axiom(g, c, OWL.hasKey, lst, m)
        if self.decision_trace:
            self.compile_decision_trace()

    def field_prop(self, entity: str, field: str) -> URIRef:
        key = (entity, field)
        if key not in self.prop_iri:
            self.prop_iri[key] = self.NS["%s.%s" % (local(entity), re.sub(r"[^A-Za-z0-9_]", "_", field))]
        return self.prop_iri[key]

    def rel_prop(self, entity: str, name: str) -> URIRef:
        slug = re.sub(r"[^A-Za-z0-9]+", "-", name.strip().lower()).strip("-")
        return self.NS["%s.%s" % (local(entity), slug)]

    def compile_relationship(self, c: URIRef, eid: str, r: dict):
        g = self.onto
        p = self.rel_prop(eid, r["name"])
        g.add((p, RDF.type, OWL.ObjectProperty))
        g.add((p, RDFS.label, Literal(r["name"])))
        g.add((p, RDFS.domain, c))
        g.add((p, RDFS.range, self.entity_node(r["target"])))
        self.annotate(g, p, r)
        for ch in r.get("characteristics") or []:
            t = {"functional": OWL.FunctionalProperty, "inverse-functional": OWL.InverseFunctionalProperty,
                 "transitive": OWL.TransitiveProperty, "symmetric": OWL.SymmetricProperty}.get(str(ch))
            if t is not None:
                g.add((p, RDF.type, t))
        if r.get("inverse"):
            inv = self.rel_prop(r["target"], str(r["inverse"]))
            g.add((inv, RDF.type, OWL.ObjectProperty))
            g.add((inv, RDFS.label, Literal(str(r["inverse"]))))
            g.add((inv, RDFS.domain, self.entity_node(r["target"])))
            g.add((inv, RDFS.range, c))
            g.add((p, OWL.inverseOf, inv))
        # cardinality: explicit counts win; the cardinality word gives max 1 for *-to-one
        mx = r.get("max_count")
        mn = r.get("min_count")
        if mx is None and str(r.get("cardinality", "")).endswith("to-one"):
            mx = 1
        for val, kind in ((mn, OWL.minCardinality), (mx, OWL.maxCardinality)):
            if val is None:
                continue
            rest = BNode()
            g.add((rest, RDF.type, OWL.Restriction))
            g.add((rest, OWL.onProperty, p))
            g.add((rest, kind, Literal(int(val), datatype=XSD.nonNegativeInteger)))
            self.annotated_axiom(g, c, RDFS.subClassOf, rest, r)

    def compile_axiom(self, c: URIRef, eid: str, a: dict):
        g = self.onto
        kind = a.get("kind")
        if kind in ("subclass_of", "disjoint_with", "equivalent_to"):
            tgt = a.get("target")
            if not tgt:
                self.notes.append("%s: axiom %s has no target" % (eid, kind))
                return
            pred = {"subclass_of": RDFS.subClassOf, "disjoint_with": OWL.disjointWith, "equivalent_to": OWL.equivalentClass}[kind]
            self.annotated_axiom(g, c, pred, self.entity_node(tgt), a)
        elif kind == "key":
            fields = a.get("fields") or []
            if not fields:
                self.notes.append("%s: key axiom has no fields" % eid)
                return
            lst = BNode()
            Collection(g, lst, [self.field_prop(eid, f) for f in fields])
            self.annotated_axiom(g, c, OWL.hasKey, lst, a)
        else:
            self.notes.append("%s: unknown axiom kind %r" % (eid, kind))

    def compile_decision_trace(self):
        """DL-23: the module every ontology carries. Classes and properties in the dt: namespace,
        aligned to PROV-O, with the minimum properties a trace record must carry."""
        g = self.onto
        D = self.DTN
        g.bind("dt", D)
        classes = {
            "Decision": ("A decision the running system or a person made about an entity, under a policy.", self.P.Activity),
            "Policy": ("A rule or policy a decision is taken under; names a rule id from rules.yaml.", self.P.Entity),
            "Exception": ("A case a policy did not cover, or a departure from it, that needed a decision.", self.P.Entity),
            "Approval": ("A person or role accepting a decision; who, when, in what capacity.", self.P.Activity),
            "Precedent": ("An earlier decision cited when deciding the current one.", self.P.Entity),
        }
        for name, (comment, parent) in classes.items():
            g.add((D[name], RDF.type, OWL.Class))
            g.add((D[name], RDFS.label, Literal(name)))
            g.add((D[name], RDFS.comment, Literal(comment)))
            g.add((D[name], RDFS.subClassOf, parent))
            g.add((D[name], self.H.confidence, Literal("confirmed")))
            g.add((D[name], self.H.evidence, Literal("module#decision-trace")))
        props = [
            ("concerns", "the entity instance the decision is about", D.Decision, OWL.Thing, OWL.ObjectProperty),
            ("underPolicy", "the policy the decision was taken under", D.Decision, D.Policy, OWL.ObjectProperty),
            ("raisedBy", "the exception that needed this decision, if any", D.Decision, D.Exception, OWL.ObjectProperty),
            ("citesPrecedent", "an earlier decision this one relied on", D.Decision, D.Precedent, OWL.ObjectProperty),
            ("approvedBy", "the approval that accepted this decision", D.Decision, D.Approval, OWL.ObjectProperty),
            ("ruleId", "the rules.yaml id the policy names", D.Policy, XSD.string, OWL.DatatypeProperty),
            ("outcome", "what was decided, in the vocabulary of the action taken", D.Decision, XSD.string, OWL.DatatypeProperty),
            ("decidedAt", "when", D.Decision, XSD.dateTime, OWL.DatatypeProperty),
            ("decidedBy", "who or which component decided", D.Decision, XSD.string, OWL.DatatypeProperty),
            ("approvedAt", "when the approval was given", D.Approval, XSD.dateTime, OWL.DatatypeProperty),
            ("approvedByRole", "the role that approved", D.Approval, XSD.string, OWL.DatatypeProperty),
        ]
        for name, comment, dom, rng, kind in props:
            g.add((D[name], RDF.type, kind))
            g.add((D[name], RDFS.label, Literal(name)))
            g.add((D[name], RDFS.comment, Literal(comment)))
            g.add((D[name], RDFS.domain, dom))
            g.add((D[name], RDFS.range, rng))
        g.add((D.decidedAt, RDFS.subPropertyOf, self.P.endedAtTime))
        g.add((D.citesPrecedent, RDFS.subPropertyOf, self.P.wasInformedBy))
        # the minimum a trace record must carry, as a shape (read by the conformance check)
        s = self.shapes
        shape = D.DecisionShape
        s.add((shape, RDF.type, SH.NodeShape))
        s.add((shape, SH.targetClass, D.Decision))
        s.add((shape, self.H.confidence, Literal("confirmed")))
        for prop, dtype in (("decidedAt", XSD.dateTime), ("decidedBy", XSD.string), ("outcome", XSD.string)):
            ps = BNode()
            s.add((shape, SH.property, ps))
            s.add((ps, SH.path, D[prop]))
            s.add((ps, SH.minCount, Literal(1)))
            s.add((ps, SH.datatype, dtype))
        for prop, cls in (("underPolicy", D.Policy),):
            ps = BNode()
            s.add((shape, SH.property, ps))
            s.add((ps, SH.path, D[prop]))
            s.add((ps, SH.minCount, Literal(1)))
            s.add((ps, SH["class"], cls))

    # -- shapes ----------------------------------------------------------------
    def compile_shapes(self):
        s = self.shapes
        mdoc = self.docs.get("mappings.yaml") or {}
        by_entity: dict[str, list[dict]] = {}
        for m in mdoc.get("mappings") or []:
            if isinstance(m, dict) and m.get("entity") in self.entities:
                by_entity.setdefault(m["entity"], []).append(m)
        for eid, e in self.entities.items():
            c = self.entity_node(eid)
            shape = self.NS[local(eid) + "Shape"]
            s.add((shape, RDF.type, SH.NodeShape))
            s.add((shape, SH.targetClass, c))
            s.add((shape, self.H.id, Literal(eid)))
            s.add((shape, self.H.confidence, Literal(e.get("confidence", "needs-review"))))
            for m in by_entity.get(eid, []):
                for f in m.get("fields") or []:
                    if not isinstance(f, dict) or not f.get("name"):
                        continue
                    ps = BNode()
                    s.add((shape, SH.property, ps))
                    p = self.field_prop(eid, f["name"])
                    s.add((ps, SH.path, p))
                    s.add((ps, SH.name, Literal(f["name"])))
                    s.add((ps, SH.description, Literal("%s.%s from %s" % (m.get("store", {}).get("name"), f["name"], m.get("id")))))
                    xt = TYPE_MAP.get(str(f.get("type", "")).lower())
                    if xt:
                        s.add((ps, SH.datatype, XSD[xt]))
                    s.add((ps, SH.maxCount, Literal(1)))
                    pct = f.get("present_pct")
                    if isinstance(pct, (int, float)) and float(pct) >= 100.0:
                        s.add((ps, SH.minCount, Literal(1)))
                    if f["name"] in (m.get("natural_key") or []):
                        s.add((ps, SH.minCount, Literal(1)))
                        s.add((ps, SH.minLength, Literal(1)))
                    self.annotate(s, ps, f)
            for r in e.get("relationships") or []:
                if not isinstance(r, dict) or not r.get("name") or not r.get("target"):
                    continue
                ps = BNode()
                s.add((shape, SH.property, ps))
                s.add((ps, SH.path, self.rel_prop(eid, r["name"])))
                s.add((ps, SH.name, Literal(r["name"])))
                s.add((ps, SH["class"], self.entity_node(r["target"])))
                mx = r.get("max_count")
                if mx is None and str(r.get("cardinality", "")).endswith("to-one"):
                    mx = 1
                if mx is not None:
                    s.add((ps, SH.maxCount, Literal(int(mx))))
                if r.get("min_count") is not None:
                    s.add((ps, SH.minCount, Literal(int(r["min_count"]))))
                self.annotate(s, ps, r)
        self.compile_actions()

    def compile_actions(self):
        """DL-29, only when actions.yaml exists: pre- and postconditions as shapes on the entities the
        action writes; each shape carries hitl:action so the reasoner can report by action."""
        adoc = self.docs.get("actions.yaml")
        if not adoc:
            return
        s = self.shapes
        for a in adoc.get("actions") or []:
            if not isinstance(a, dict) or not a.get("id"):
                continue
            node = self.NS[local(a["id"])]
            s.add((node, RDF.type, self.H.Action))
            s.add((node, RDFS.label, Literal(a.get("name", a["id"]))))
            self.annotate(s, node, a, a["id"])
            for key, pred in (("reads", self.H.reads), ("writes", self.H.writes)):
                for ref in a.get(key) or []:
                    s.add((node, pred, Literal(str(ref))))
            for role in a.get("roles") or []:
                s.add((node, self.H.role, Literal(str(role))))
            for rid in a.get("rules") or []:
                s.add((node, self.H.governedBy, Literal(str(rid))))
            if a.get("emits"):
                s.add((node, self.H.emits, Literal(str(a["emits"]))))
            for key, pred in (("preconditions", self.H.precondition), ("postconditions", self.H.postcondition)):
                for i, cond in enumerate(a.get(key) or []):
                    if not isinstance(cond, dict) or not cond.get("target") or not cond.get("sparql"):
                        continue
                    shape = self.NS["%s.%s.%d" % (local(a["id"]), key[:-1], i + 1)]
                    s.add((shape, RDF.type, SH.NodeShape))
                    s.add((shape, SH.targetClass, self.entity_node(cond["target"])))
                    s.add((shape, self.H.action, node))
                    s.add((node, pred, shape))
                    c = BNode()
                    s.add((shape, SH.sparql, c))
                    s.add((c, SH.message, Literal(cond.get("message", "%s %s %d" % (a["id"], key[:-1], i + 1)))))
                    s.add((c, SH.select, Literal(self.with_prefixes(cond["sparql"]))))
                    s.add((shape, self.H.confidence, Literal(a.get("confidence", "needs-review"))))

    # -- rules -----------------------------------------------------------------
    def with_prefixes(self, body: str) -> str:
        head = "PREFIX : <%s>\nPREFIX hitl: <%s>\nPREFIX dt: <%s>\nPREFIX xsd: <%s>\nPREFIX rdf: <%s>\nPREFIX rdfs: <%s>\n" % (
            self.base, HITL, DT, str(XSD), str(RDF), str(RDFS))
        return head + body if "PREFIX" not in body.upper() else body

    def compile_rules(self):
        rdoc = self.docs.get("rules.yaml")
        if not rdoc:
            return
        g = self.rules
        for r in rdoc.get("rules") or []:
            if not isinstance(r, dict) or not r.get("id") or not isinstance(r.get("formal"), dict):
                continue
            fm = r["formal"]
            tgt = fm.get("target")
            if tgt not in self.entities:
                self.notes.append("%s: formal.target %r is not an entity" % (r["id"], tgt))
                continue
            shape = self.NS[local(r["id"]) + "Shape"]
            g.add((shape, RDF.type, SH.NodeShape))
            g.add((shape, SH.targetClass, self.entity_node(tgt)))
            g.add((shape, RDFS.label, Literal(r.get("statement", r["id"]))))
            self.annotate(g, shape, r, r["id"])
            if r.get("status"):
                g.add((shape, self.H.status, Literal(str(r["status"]))))
            if r.get("owner"):
                g.add((shape, self.H.owner, Literal(str(r["owner"]))))
            if r.get("why"):
                g.add((shape, self.H.why, Literal(str(r["why"]))))
            rule = BNode()
            g.add((shape, SH.rule, rule))
            body = fm.get("body")
            if fm.get("kind") == "sparql":
                g.add((rule, RDF.type, SH.SPARQLRule))
                g.add((rule, SH.construct, Literal(self.with_prefixes(str(body)))))
            elif fm.get("kind") == "triple" and isinstance(body, dict):
                g.add((rule, RDF.type, SH.TripleRule))
                g.add((rule, SH.subject, SH.this))
                g.add((rule, SH.predicate, self.term(body.get("predicate"))))
                g.add((rule, SH.object, self.term(body.get("object"))))
            else:
                self.notes.append("%s: formal.kind %r needs a body" % (r["id"], fm.get("kind")))
            # a rule may carry a condition: only instances passing this shape fire it
            if fm.get("condition"):
                cond = BNode()
                g.add((rule, SH.condition, cond))
                g.add((cond, RDF.type, SH.NodeShape))
                c = BNode()
                g.add((cond, SH.sparql, c))
                g.add((c, SH.select, Literal(self.with_prefixes(str(fm["condition"])))))

    def term(self, v):
        if isinstance(v, str) and v.startswith(("http://", "https://")):
            return URIRef(v)
        if isinstance(v, str) and v.startswith(":"):
            return self.NS[v[1:]]
        if isinstance(v, str) and v.startswith("dt:"):
            return self.DTN[v[3:]]
        if isinstance(v, bool):
            return Literal(v)
        return Literal(v)

    # -- run ---------------------------------------------------------------------
    def run(self, out_dir: str) -> dict:
        for name in FOUR + OPTIONAL:
            self.docs[name] = load(os.path.join(self.d, name))
        self.compile_ontology()
        self.compile_shapes()
        self.compile_rules()
        os.makedirs(out_dir, exist_ok=True)
        outputs = {}
        for fname, g in (("ontology.ttl", self.onto), ("shapes.ttl", self.shapes), ("rules.ttl", self.rules)):
            p = os.path.join(out_dir, fname)
            g.serialize(destination=p, format="turtle")
            outputs[fname] = {"triples": len(g), "sha256": sha(p)}
        inputs = {}
        for name in FOUR + OPTIONAL:
            p = os.path.join(self.d, name)
            if os.path.exists(p):
                inputs[name] = sha(p)
        pin = {
            "schema_version": "1.1",
            "compiled_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "compiler": {"name": "compile_ontology.py", "version": VERSION},
            "base_iri": self.base,
            "inputs": inputs,
            "outputs": outputs,
            "decision_trace": "on" if self.decision_trace else "off",
        }
        with open(os.path.join(out_dir, "pin.yaml"), "w", encoding="utf-8") as f:
            yaml.safe_dump(pin, f, sort_keys=False)
        return pin


def read_config(repo_root: str) -> dict:
    cfg = load(os.path.join(repo_root, ".hitl", "config.yaml")) or {}
    return (cfg.get("data_layer") or {}) if isinstance(cfg, dict) else {}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", default="docs/02-design/data")
    ap.add_argument("--root", default=".", help="repo root, for .hitl/config.yaml")
    ap.add_argument("--base", default=None, help="base IRI; default from .hitl/config.yaml data_layer.base_iri, else %s" % DEFAULT_BASE)
    ap.add_argument("--out", default=None, help="output dir; default <data-dir>/compiled")
    a = ap.parse_args(argv)
    if not HAVE_RDFLIB:
        print("SKIPPED: rdflib not installed (pip install rdflib); the data layer was not compiled.")
        return 0
    if not os.path.isdir(a.data_dir):
        print("data layer: absent (%s)" % a.data_dir)
        return 0
    cfg = read_config(a.root)
    base = a.base or cfg.get("base_iri") or DEFAULT_BASE
    dtrace = str(cfg.get("decision_trace", "on")).lower() != "off"
    if not dtrace and not cfg.get("decision_trace_reason"):
        print("ERROR: data_layer.decision_trace is off with no decision_trace_reason in .hitl/config.yaml (DL-23: removing the module is a recorded decision)")
        return 2
    comp = Compiler(a.data_dir, base, dtrace)
    pin = comp.run(a.out or os.path.join(a.data_dir, "compiled"))
    for n in comp.notes:
        print("note: " + n)
    print("compiled: %s" % ", ".join("%s (%d triples)" % (k, v["triples"]) for k, v in pin["outputs"].items()))
    print("decision-trace module: %s; base %s" % (pin["decision_trace"], pin["base_iri"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
