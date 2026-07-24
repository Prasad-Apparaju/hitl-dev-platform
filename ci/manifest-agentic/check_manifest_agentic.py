#!/usr/bin/env python3
"""Compound-agentic manifest validator (EPIC #10 / LLD §6) — value-checking,
fail-closed, PER-CHECK ACTIVATED.

Each check runs iff its activation predicate holds over the human-authored manifest;
its registry is loaded only when it activates (ADR-13). A legacy/deterministic
manifest activates nothing new and needs no registry. Aggregates all blockers, then
exits 2 if any un-waived blocker stands, else 0. Fails closed on unparseable input,
unknown enum, unresolved reference, or any exception.

Waves land incrementally (05-implementation-plan.md §3). Implemented so far:
  wave 1  activation dispatch + additivity + waiver suppression + main
  wave 2  check_topology, check_references, check_classification, check_scope_grammar
"""
from __future__ import annotations
import os
import re
import sys
from collections import namedtuple

Blocker = namedtuple("Blocker", "locus code message severity")
def block(locus, code, message):   return Blocker(locus, code, message, "block")
def warn(locus, code, message):    return Blocker(locus, code, message, "warning")

# ── grammars (§0) ────────────────────────────────────────────────────────────
ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")                 # interaction_id / domain_name
SCOPE_RE = re.compile(r"^[a-z][a-z0-9_]*:(?:\*|[a-z0-9_][a-z0-9_.*/-]*)$")  # "op:resource" | "op:*"
DURATION_RE = re.compile(r"^[0-9]+(?:ms|s|m|h|d)$")
AGENT_KINDS = {"simple_agent", "deep_agent"}
NON_WAIVABLE = {"unparseable", "unknown_field", "schema_invalid"}

REGISTRY_DIR = "docs/03-engineering"


# ── manifest accessors ───────────────────────────────────────────────────────
def domains(m):        return m.get("domains") or {}
def interactions(m):   return m.get("interactions") or []
def segments(m):       return m.get("segments") or []
def sagas(m):          return m.get("sagas") or []

def kind_of(m, dname):
    d = domains(m).get(dname) or {}
    return d.get("kind") or "deterministic"

def is_agent(m, dname):
    return kind_of(m, dname) in AGENT_KINDS

def any_agent(m):
    return any((d.get("kind") in AGENT_KINDS) for d in domains(m).values())


# ── registries (lazy; loaded only when a check activates — §6.0) ──────────────
class Registries:
    """Loads a registry file on first request from the registry dir; caches it.
    A missing/malformed registry needed by an active check is a fail-closed
    system:/registry: blocker (non-waivable)."""
    FILES = {
        "capabilities": "approved-capabilities.yaml",
        "policies": "policies.yaml",
        "stores": "stores.yaml",
        "evals_index": "evals/index.yaml",
        "evals_waivers": "evals/waivers.yaml",
    }
    def __init__(self, root):
        self.root = root
        self._cache = {}
        self.errors = []

    def get(self, name):
        if name in self._cache:
            return self._cache[name]
        import yaml
        path = os.path.join(self.root, REGISTRY_DIR, self.FILES[name])
        try:
            with open(path) as f:
                data = yaml.safe_load(f)
            if not isinstance(data, dict) or data.get("schema_version") is None:
                raise ValueError("missing schema_version or not a mapping")
        except Exception as e:  # noqa: BLE001 — fail closed on any registry problem
            self.errors.append(block(f"registry:{name}", "schema_invalid",
                                     f"registry {self.FILES[name]} unreadable/invalid: {e}"))
            data = None
        self._cache[name] = data
        return data


# ══════════════════════════════════════════════════════════════════════════════
# Checks — each returns list[Blocker]. Wave 2: graph integrity.
# ══════════════════════════════════════════════════════════════════════════════

def check_topology(m, reg, tier):
    """§6.5: dup ids, incomplete interaction (§4.1), uncontrolled cycle, coordinator/
    pattern rule, empty orchestration.justification, non-consecutive segment paths."""
    out = []
    ids = [i.get("id") for i in interactions(m)]
    seen = set()
    for iid in ids:
        if iid in seen:
            out.append(block(iid, "duplicate_interaction_id", f"interaction id '{iid}' is not unique"))
        seen.add(iid)

    # interaction requiredness by kind (§4.1)
    for i in interactions(m):
        iid = i.get("id", "?")
        k = i.get("kind")
        if k in ("sync_call", "async_task", "event") and not i.get("facade"):
            out.append(block(iid, "interaction_incomplete", f"{k} '{iid}' missing required facade"))
        if k == "sync_call" and i.get("response") is None:
            out.append(block(iid, "interaction_incomplete", f"sync_call '{iid}' requires a response leg"))
        if k == "sync_call" and i.get("async") is not None:
            out.append(block(iid, "interaction_incomplete", f"sync_call '{iid}' forbids an async block"))
        if k == "async_task" and i.get("async") is None:
            out.append(block(iid, "interaction_incomplete", f"async_task '{iid}' requires an async block"))
        if k == "event" and i.get("response") is not None:
            out.append(block(iid, "interaction_incomplete", f"event '{iid}' forbids a response leg"))

    # cycle detection over the domain graph, guarded by orchestration.cycle_bound
    adj = {}
    for i in interactions(m):
        adj.setdefault(i.get("from"), set()).add(i.get("to"))
    if _has_cycle(adj):
        cb = (m.get("orchestration") or {}).get("cycle_bound")
        if not (isinstance(cb, int) and cb > 0):
            out.append(block("system:topology", "uncontrolled_cycle",
                             "interaction graph has a cycle but orchestration.cycle_bound is not a positive int"))

    orch = m.get("orchestration")
    if orch is not None:
        if not (orch.get("justification") or "").strip():
            out.append(block("system:orchestration", "orchestration_justification_missing",
                             "orchestration.justification is required and non-empty (CR-11)"))
        pat, coord = orch.get("pattern"), orch.get("coordinator")
        if pat in ("supervisor", "hierarchical", "blackboard"):
            if not coord:
                out.append(block("system:orchestration", "coordinator_required",
                                 f"pattern '{pat}' requires a coordinator agent"))
            elif not is_agent(m, coord):
                out.append(block("system:orchestration", "coordinator_not_agent",
                                 f"coordinator '{coord}' must be an agent domain"))
        if pat == "swarm" and coord:
            out.append(block("system:orchestration", "coordinator_forbidden",
                             "pattern 'swarm' forbids a coordinator (peer mesh)"))

    by_id = {i.get("id"): i for i in interactions(m)}
    for s in segments(m):
        path = s.get("path") or []
        for a, b in zip(path, path[1:]):
            ia, ib = by_id.get(a), by_id.get(b)
            if ia and ib and ia.get("to") != ib.get("from"):
                out.append(block(s.get("id", "?"), "segment_path_noncontiguous",
                                 f"segment '{s.get('id')}': hop {a}.to != {b}.from"))
    return out


def check_references(m, reg, tier):
    """§6.6: facade/domain resolution, event reconciliation, double-authoring."""
    out = []
    dset = set(domains(m))
    for i in interactions(m):
        iid = i.get("id", "?")
        frm, to = i.get("from"), i.get("to")
        if frm not in dset:
            out.append(block(iid, "unknown_domain", f"interaction '{iid}' from '{frm}' is not a declared domain"))
        if to not in dset:
            out.append(block(iid, "unknown_domain", f"interaction '{iid}' to '{to}' is not a declared domain"))
        fac = i.get("facade") or ""
        if ":" in fac and to in dset:
            owner, api = fac.split(":", 1)
            if i.get("kind") == "event":
                if owner != frm:
                    out.append(block(iid, "event_ref_unresolved",
                                     f"event '{iid}' facade producer '{owner}' != from '{frm}'"))
            else:
                fac_apis = (domains(m).get(to) or {}).get("facade_apis") or {}
                if owner != to or api not in fac_apis:
                    out.append(block(iid, "facade_unresolved",
                                     f"interaction '{iid}' facade '{fac}' does not resolve to {to}.facade_apis"))
    # double-authoring: a hand-authored interaction_matrix alongside interactions
    if interactions(m) and m.get("interaction_matrix"):
        out.append(block("system:interactions", "edge_double_authored",
                         "interaction_matrix is hand-authored in the manifest alongside `interactions` "
                         "(it must be a generated projection, §2.4)"))
    return out


def check_classification(m, reg, tier):
    """§6.15: in a compound manifest, every agent domain needs kind_rationale (CR-2)."""
    out = []
    for name, d in domains(m).items():
        if d.get("kind") in AGENT_KINDS and not (d.get("kind_rationale") or "").strip():
            out.append(block(name, "kind_rationale_missing",
                             f"agent domain '{name}' must state kind_rationale (simplest-fit, CR-2)"))
    return out


def check_scope_grammar(m, reg, tier):
    """§6.13: every Scope (identity.privilege, uses-derived, authority_bound, ceilings)
    matches the grammar."""
    out = []
    def check(scope, locus):
        if not isinstance(scope, str) or not SCOPE_RE.match(scope):
            out.append(block(locus, "scope_grammar", f"ill-formed scope '{scope}' (expected op:resource)"))
    for name, d in domains(m).items():
        for sc in (d.get("identity") or {}).get("privilege", []):
            check(sc, name)
        for u in d.get("uses", []):
            for op in u.get("operations", []):
                for res in (u.get("resources") or ["*"]):
                    check(f"{op}:{res}", name)
    for i in interactions(m):
        for leg in ("request", "response"):
            for sc in ((i.get(leg) or {}).get("authority_bound") or []):
                check(sc, i.get("id", "?"))
    return out


# ══════════════════════════════════════════════════════════════════════════════
# Cycle helper
# ══════════════════════════════════════════════════════════════════════════════
def _has_cycle(adj):
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {}
    nodes = set(adj) | {v for vs in adj.values() for v in vs}
    def dfs(u):
        color[u] = GRAY
        for v in adj.get(u, ()):
            c = color.get(v, WHITE)
            if c == GRAY or (c == WHITE and dfs(v)):
                return True
        color[u] = BLACK
        return False
    return any(color.get(n, WHITE) == WHITE and dfs(n) for n in nodes)


# ══════════════════════════════════════════════════════════════════════════════
# Activation dispatch (§6.0) — (check, predicate, needed registries)
# ══════════════════════════════════════════════════════════════════════════════
def _has_typed_interactions(m):   return bool(interactions(m))
def _compound_with_agent(m):
    ep = any(is_agent(m, i.get("from")) or is_agent(m, i.get("to")) for i in interactions(m))
    return bool(interactions(m)) and ep
def _any_scope(m):
    return any((d.get("identity") or {}).get("privilege") or d.get("uses") for d in domains(m).values()) \
        or any((i.get(leg) or {}).get("authority_bound") for i in interactions(m) for leg in ("request", "response"))

DISPATCH = [
    # (name, fn, predicate, [registries])
    ("check_topology",       check_topology,       lambda m: _has_typed_interactions(m) or m.get("orchestration") or segments(m), []),
    ("check_references",     check_references,     _has_typed_interactions, []),
    ("check_classification", check_classification, _compound_with_agent, []),
    ("check_scope_grammar",  check_scope_grammar,  _any_scope, []),
]


# ── waivers (§6, general manifest-waivers.yaml) ───────────────────────────────
def load_waivers(root):
    import yaml, datetime
    path = os.path.join(root, "ci/manifest-agentic/manifest-waivers.yaml")
    if not os.path.exists(path):
        return [], []
    try:
        data = yaml.safe_load(open(path)) or {}
        assert data.get("schema_version") is not None
        rows = data.get("waivers") or []
        seen, errs = set(), []
        for w in rows:
            for k in ("code", "locus", "owner", "reason", "tier_limit", "revisit"):
                if w.get(k) in (None, ""):
                    errs.append(block("system:waivers", "schema_invalid", f"waiver missing {k}"))
            key = (w.get("code"), w.get("locus"))
            if key in seen:
                errs.append(block("system:waivers", "schema_invalid", f"duplicate waiver {key}"))
            seen.add(key)
        return rows, errs
    except Exception as e:  # noqa: BLE001 — malformed waiver file fails closed
        return None, [block("system:waivers", "schema_invalid", f"manifest-waivers.yaml invalid: {e}")]


def _waived(b, waivers, tier, today):
    import datetime
    if b.code in NON_WAIVABLE or b.locus.startswith(("system:", "registry:")):
        return False
    for w in waivers:
        if w.get("code") == b.code and w.get("locus") == b.locus \
           and tier <= int(w["tier_limit"]) and _date(w["revisit"]) >= today:
            return True
    return False


def _date(v):
    import datetime
    if isinstance(v, datetime.date):
        return v
    return datetime.date.fromisoformat(str(v))


# ── main ──────────────────────────────────────────────────────────────────────
def run(manifest, root, tier):
    """Return (blockers_standing, warnings, waived, activated_names)."""
    import datetime
    reg = Registries(root)
    activated, produced = [], []
    for name, fn, pred, needs in DISPATCH:
        if pred(manifest):
            activated.append(name)
            for rname in needs:
                reg.get(rname)
            produced.extend(fn(manifest, reg, tier))
    produced.extend(reg.errors)

    waivers, werrs = load_waivers(root)
    if waivers is None:  # malformed → fail closed, nothing waived
        waivers = []
    produced.extend(werrs)

    today = datetime.date.today()
    standing, warnings, waived = [], [], []
    for b in produced:
        if b.severity == "warning":
            warnings.append(b)
        elif _waived(b, waivers, tier, today):
            waived.append(b)
        else:
            standing.append(b)
    return standing, warnings, waived, activated


def main(argv=None):
    import argparse, yaml
    ap = argparse.ArgumentParser(description="Compound-agentic manifest validator (#10)")
    ap.add_argument("manifest")
    ap.add_argument("--root", default=".")
    ap.add_argument("--tier", type=int, default=None)
    a = ap.parse_args(argv)
    try:
        m = yaml.safe_load(open(a.manifest))
        assert isinstance(m, dict)
    except Exception as e:  # noqa: BLE001
        print(f"BLOCK unparseable system:manifest — {e}")
        return 2
    tier = a.tier if a.tier is not None else 3  # absent ⇒ highest (fail-safe)
    standing, warnings, waived, activated = run(m, a.root, tier)
    for b in warnings: print(f"WARN  {b.code} {b.locus} — {b.message}")
    for b in waived:   print(f"WAIVED {b.code} {b.locus}")
    for b in standing: print(f"BLOCK {b.code} {b.locus} — {b.message}")
    print(f"\nactivated: {', '.join(activated) or '(none)'} | "
          f"{len(standing)} blocker(s), {len(warnings)} warning(s), {len(waived)} waived | tier {tier}")
    return 2 if standing else 0


if __name__ == "__main__":
    sys.exit(main())
