#!/usr/bin/env python3
"""Generated views for the compound-agentic surface (EPIC #10 / LLD §2.4, §9).

`generate(manifest)` produces DETERMINISTIC, paired machine-readable + rendered
artifacts under docs/03-engineering/agentic-posture/ — plus the eval-coverage index
(a projection of the inline evals.spec fields) at docs/03-engineering/evals/index.yaml.
None of these is written back into the source manifest (round-3 B1); they are separate
generated files so the validator's edge_double_authored / eval_index_mismatch cannot be
tripped by the generator itself.

Modes:
  --write   (default) regenerate all views/index on disk
  --check   regenerate in memory and DIFF against disk; exit 2 on drift
            (the "cannot drift" regenerate-and-diff guarantee, §9)

Static only — no runtime, no server (ADR-5). Governs-not-runtime: the product builds
the trace backend/console; this only renders the declared posture.
"""
from __future__ import annotations
import json
import os
import sys

POSTURE_DIR = "docs/03-engineering/agentic-posture"
EVAL_INDEX = "docs/03-engineering/evals/index.yaml"
AGENT_KINDS = {"simple_agent", "deep_agent"}


# ── accessors ─────────────────────────────────────────────────────────────────
def _domains(m):      return m.get("domains") or {}
def _interactions(m): return m.get("interactions") or []
def _segments(m):     return m.get("segments") or []
def _kind(m, d):      return (_domains(m).get(d) or {}).get("kind") or "deterministic"


# ── projections (§2.4) ────────────────────────────────────────────────────────
def project_eval_index(m):
    rows = []
    for name in sorted(_domains(m)):
        sp = (_domains(m)[name].get("evals") or {}).get("spec")
        if sp:
            rows.append({"target_type": "component", "target_id": name, "spec_path": sp})
    for i in sorted(_interactions(m), key=lambda x: x.get("id", "")):
        sp = (i.get("evals") or {}).get("spec")
        if sp:
            rows.append({"target_type": "interaction", "target_id": i.get("id"), "spec_path": sp})
    for s in sorted(_segments(m), key=lambda x: x.get("id", "")):
        sp = (s.get("evals") or {}).get("spec")
        if sp:
            rows.append({"target_type": "segment", "target_id": s.get("id"), "spec_path": sp})
    return rows


def project_interaction_matrix(m):
    pairs = {}
    for i in sorted(_interactions(m), key=lambda x: x.get("id", "")):
        key = f"{i.get('from')} -> {i.get('to')}"
        pairs.setdefault(key, {"descriptions": [], "entity_crossing": []})
        pairs[key]["descriptions"].append(i.get("description", ""))
        pairs[key]["entity_crossing"].append(i.get("entity_crossing", ""))
    return {k: {"description": "\n".join(v["descriptions"]),
                "entity_crossing": " | ".join(x for x in v["entity_crossing"] if x)}
            for k, v in sorted(pairs.items())}


def project_depends_on(m):
    dep = {}
    for i in _interactions(m):
        dep.setdefault(i.get("from"), set()).add(i.get("to"))
    return {k: sorted(v) for k, v in sorted(dep.items())}


def project_events(m):
    emitted, consumed = {}, {}
    for i in sorted(_interactions(m), key=lambda x: x.get("id", "")):
        if i.get("kind") != "event":
            continue
        p, c, fac = i.get("from"), i.get("to"), i.get("facade") or ""
        ev = fac.split(":", 1)[1] if ":" in fac else fac
        emitted.setdefault(p, []).append({"name": ev, "shape": i.get("entity_crossing", ""), "consumed_by": c})
        consumed.setdefault(c, []).append({"name": ev, "from": p})
    return {"events_emitted": emitted, "events_consumed": consumed}


def project_privilege(m):
    out = {}
    for name in sorted(_domains(m)):
        d = _domains(m)[name]
        ident = d.get("identity") or {}
        out[name] = {
            "kind": _kind(m, name),
            "principal": ident.get("principal"),
            "granted": sorted(ident.get("privilege", [])),
            "uses": sorted(f"{u.get('capability')}:{op}:{res}"
                           for u in (d.get("uses") or [])
                           for op in u.get("operations", [])
                           for res in (u.get("resources") or ["*"])),
        }
    return out


def project_tool_matrix(m, caps):
    """class:tool projection of the capability registry × domain usage (CR-15)."""
    tools = {n: c for n, c in (caps or {}).items() if c.get("class") == "tool"}
    rows = {}
    for name in sorted(_domains(m)):
        for u in (_domains(m)[name].get("uses") or []):
            cap = u.get("capability")
            if cap in tools:
                rows.setdefault(cap, {"runtime_ref": tools[cap].get("runtime_ref"), "used_by": []})
                rows[cap]["used_by"].append(name)
    for cap in rows:
        rows[cap]["used_by"] = sorted(set(rows[cap]["used_by"]))
    return rows


# ── topology render (Mermaid) ─────────────────────────────────────────────────
_SHAPE = {"simple_agent": ("{{", "}}"), "deep_agent": ("{{", "}}"),
          "deterministic": ("[", "]")}
_EDGE = {"sync_call": "-->", "async_task": "-. async .->", "event": "-. event .->"}

def render_topology_md(m):
    lines = ["# Topology (generated — do not edit)", "",
             f"Orchestration: **{(m.get('orchestration') or {}).get('pattern', 'n/a')}**", "",
             "```mermaid", "graph LR"]
    for name in sorted(_domains(m)):
        lo, hi = _SHAPE.get(_kind(m, name), ("[", "]"))
        lines.append(f"  {name}{lo}{name} · {_kind(m, name)}{hi}")
    for i in sorted(_interactions(m), key=lambda x: x.get("id", "")):
        arrow = _EDGE.get(i.get("kind"), "-->")
        lines.append(f"  {i.get('from')} {arrow}|{i.get('id')}| {i.get('to')}")
    lines += ["```", ""]
    return "\n".join(lines) + "\n"


# ── emit ──────────────────────────────────────────────────────────────────────
def _jdump(obj):
    return json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n"

def build_artifacts(m, caps):
    """Return {relative_path: text} for every generated artifact (deterministic)."""
    has_interactions = bool(_interactions(m))
    proj = {"schema_version": "1.0"}
    if has_interactions:
        proj["interaction_matrix"] = project_interaction_matrix(m)
        proj["depends_on"] = project_depends_on(m)
        proj.update(project_events(m))
    priv = {"schema_version": "1.0", "domains": project_privilege(m)}
    topo = {"schema_version": "1.0",
            "orchestration": (m.get("orchestration") or {}).get("pattern"),
            "nodes": {n: _kind(m, n) for n in sorted(_domains(m))},
            "edges": [{"id": i.get("id"), "from": i.get("from"), "to": i.get("to"), "kind": i.get("kind")}
                      for i in sorted(_interactions(m), key=lambda x: x.get("id", ""))]}
    tools = {"schema_version": "1.0", "tools": project_tool_matrix(m, caps)}
    ob = m.get("observability") or {}
    tr = ob.get("tracing") or {}
    ec = ob.get("eval_console") or {}
    agent_hops = sorted(i.get("id") for i in _interactions(m)
                        if _kind(m, i.get("from")) in AGENT_KINDS or _kind(m, i.get("to")) in AGENT_KINDS)
    obs = {"schema_version": "1.0",
           "declared": bool(ob),
           "convention": tr.get("convention"),
           "traced_hops": sorted(tr.get("hops") or []),
           "agent_hops": agent_hops,
           "attributes": sorted(tr.get("attributes") or []),
           "cost_budget": ob.get("cost_budget"),
           "eval_console": {"access": ec.get("access"), "owner": ec.get("owner"), "ref": ec.get("ref")}}
    idx_rows = project_eval_index(m)
    eval_index = ("# GENERATED by tools/manifest-agentic/generate_views.py — do not edit (§7.1).\n"
                  "# A projection of the inline evals.spec fields; regenerate-and-diff enforced.\n"
                  "schema_version: \"1.0\"\n"
                  + ("rows: []\n" if not idx_rows else "rows:\n"
                     + "".join(f"  - {{ target_type: {r['target_type']}, target_id: {r['target_id']}, "
                               f"spec_path: \"{r['spec_path']}\" }}\n" for r in idx_rows)))
    return {
        f"{POSTURE_DIR}/projections.json": _jdump(proj),
        f"{POSTURE_DIR}/topology.json": _jdump(topo),
        f"{POSTURE_DIR}/topology.md": render_topology_md(m),
        f"{POSTURE_DIR}/privilege-posture.json": _jdump(priv),
        f"{POSTURE_DIR}/tool-matrix.json": _jdump(tools),
        f"{POSTURE_DIR}/observability-posture.json": _jdump(obs),
        EVAL_INDEX: eval_index,
    }


def generate(manifest_path, root, write=True):
    import yaml
    m = yaml.safe_load(open(manifest_path))
    caps_path = os.path.join(root, "docs/03-engineering/approved-capabilities.yaml")
    caps = (yaml.safe_load(open(caps_path)).get("capabilities") if os.path.exists(caps_path) else {}) or {}
    arts = build_artifacts(m, caps)
    drift = []
    for rel, text in arts.items():
        path = os.path.join(root, rel)
        current = open(path).read() if os.path.exists(path) else None
        if current != text:
            drift.append(rel)
        if write:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as f:
                f.write(text)
    return drift


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="Generate compound-agentic posture views + eval index (#10)")
    ap.add_argument("manifest")
    ap.add_argument("--root", default=".")
    ap.add_argument("--check", action="store_true", help="diff against disk; exit 2 on drift")
    a = ap.parse_args(argv)
    drift = generate(a.manifest, a.root, write=not a.check)
    if a.check and drift:
        for d in drift:
            print(f"DRIFT {d} — regenerate with generate_views.py")
        return 2
    print(("checked, no drift" if a.check else "wrote") + f": {len(build_artifacts(__import__('yaml').safe_load(open(a.manifest)), {}))} artifacts")
    return 0


if __name__ == "__main__":
    sys.exit(main())
