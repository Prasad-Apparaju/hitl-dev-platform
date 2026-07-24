"""Manifest writer: canonical state (scenario + authored.*) → a #10 manifest dict (Advisor LLD §5.1/§7.1.1).
Fixed key rule: component.id → domains[id], edge.id → interactions[] element. Additive; only writes owned
keys. If a required field is absent from `authored`, the produced manifest fails #10 — the B2 test.
"""


def write_manifest(state):
    a = state.get("authored", {})
    domains = {}
    for c in state["components"]:
        domains[c["id"]] = {"kind": c.get("kind"), "kind_rationale": c.get("kind_rationale")}

    # classify: deep_agent block
    for da in a.get("deep_agents", []):
        domains[da["component_id"]]["deep_agent"] = {
            "planner": da["planner"], "subagents": da["subagents"],
            "context_isolation": da["context_isolation"], "gates": da["gates"], "guardrails": da["guardrails"],
        }
    # boundary: facades
    for f in a.get("facades", []):
        domains.setdefault(f["on"], {}).setdefault("facade_apis", {})[f["name"]] = {
            "signature": f["signature"], "blurb": f["blurb"],
            "mutations": f.get("mutations", []), "preconditions": f.get("preconditions", []),
            "error_modes": f.get("error_modes", []),
        }
    # privilege: identity + uses
    for idn in a.get("identities", []):
        domains[idn["component_id"]]["identity"] = {"principal": idn["principal"], "privilege": idn.get("privilege", [])}
        domains[idn["component_id"]]["uses"] = idn.get("uses", [])
    # memory
    for mem in a.get("memory", []):
        domains[mem["component_id"]]["memory"] = {"short_term": mem.get("short_term"), "long_term": mem.get("long_term")}
    # lifecycle
    for lc in a.get("lifecycle", []):
        domains[lc["component_id"]]["lifecycle"] = {k: v for k, v in lc.items() if k != "component_id"}

    # interactions (edges + boundary legs + authorization + async)
    legs = {}
    for l in a.get("legs", []):
        legs.setdefault(l["edge_id"], {})[l["leg"]] = {k: v for k, v in l.items() if k not in ("edge_id", "leg")}
    authz = {z["edge_id"]: {k: v for k, v in z.items() if k != "edge_id"} for z in a.get("authorizations", [])}
    async_ = {x["edge_id"]: {k: v for k, v in x.items() if k != "edge_id"} for x in a.get("async", [])}
    facade_of = {(f["on"], f["name"]): f["name"] for f in a.get("facades", [])}
    interactions = []
    for e in state["edges"]:
        i = {"id": e["id"], "from": e["from"], "to": e["to"], "kind": e.get("kind")}
        # attach a facade on the callee if one was authored
        for (on, name) in facade_of:
            if on == e["to"]:
                i["facade"] = name
                break
        i.update(legs.get(e["id"], {}))
        if e["id"] in authz:
            i["authorization"] = authz[e["id"]]
        if e["id"] in async_:
            i["async"] = async_[e["id"]]
        interactions.append(i)

    m = {"domains": domains, "interactions": interactions}
    if a.get("segments"):
        m["segments"] = a["segments"]
    if a.get("orchestration"):
        m["orchestration"] = a["orchestration"]
    if a.get("sagas"):
        m["sagas"] = a["sagas"]
    if a.get("evals"):
        m["evals"] = a["evals"]
    if a.get("observability"):
        m["observability"] = a["observability"]
    if a.get("policies"):
        m["policies"] = a["policies"]
    if a.get("stores"):
        m["stores"] = a["stores"]
    return m
