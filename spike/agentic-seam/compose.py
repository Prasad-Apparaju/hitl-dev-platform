"""The Advisor composer — floor DERIVED from #10's activation, IMPORTED (no copy). Round-7 B1."""

from activation import ACTIVATES  # THE single source; the composer never restates a predicate.

COMMANDS = ["agentic-classify", "agentic-boundary", "agentic-privilege", "agentic-reliability",
            "agentic-observability", "agentic-memory", "agentic-evals", "agentic-deploy"]
DEPENDS = {c: ["agentic-classify"] for c in COMMANDS if c != "agentic-classify"}
DEPENDS["agentic-reliability"] = ["agentic-boundary"]

# PRIMARY checks decide floor MEMBERSHIP.
PRIMARY_CHECKS = {
    "agentic-classify":      ["check_classification", "check_deep_agent"],
    "agentic-boundary":      ["check_boundary_legs", "check_topology", "check_references", "check_authorization"],
    "agentic-privilege":     ["check_capabilities"],
    "agentic-reliability":   ["check_async", "check_lifecycle", "check_saga"],
    "agentic-observability": ["check_observability"],
    "agentic-memory":        ["check_memory"],
    "agentic-evals":         ["check_eval_coverage"],
    "agentic-deploy":        [],
}
# SECONDARY (downstream) checks — owned for validity, NOT for membership.
SECONDARY_OWNERS = {
    "check_policy_refs":   ["agentic-boundary", "agentic-reliability", "agentic-memory"],
    "check_scope_grammar": ["agentic-privilege", "agentic-boundary"],
}
OWNS_CHECKS = {c: list(PRIMARY_CHECKS[c]) + [k for k, ow in SECONDARY_OWNERS.items() if c in ow]
               for c in PRIMARY_CHECKS}


def check_ownership_complete():
    """Every BLOCKING check is owned by some command; every owned name is a real check (round-7 B1)."""
    owned = {c for names in OWNS_CHECKS.values() for c in names}
    missing = set(ACTIVATES) - owned
    unreal = owned - set(ACTIVATES)
    assert not missing, f"unowned activatable checks: {missing}"
    assert not unreal, f"OWNS_CHECKS names non-checks: {unreal}"


def features_from_scenario(s):
    """The composer's prediction of the manifest features the authored manifest WILL have."""
    agent = {"simple_agent", "deep_agent"}
    kind = {c["id"]: c["kind"] for c in s["components"]}
    is_ag = lambda n: kind.get(n) in agent
    edges = s["edges"]
    a = s["answers"]
    return {
        "any_agent":               any(k in agent for k in kind.values()),
        "any_deep_agent":          any(k == "deep_agent" for k in kind.values()),
        "has_interactions":        len(edges) > 0,
        "orchestration_or_segments": False,
        "agent_endpoint":          any(is_ag(e["from"]) or is_ag(e["to"]) for e in edges),
        "into_agent":              any(is_ag(e["to"]) for e in edges),
        "declares_authorization":  False,  # boundary authors it; predicted via into_agent above
        "any_async":               any(e.get("kind") in ("async_task", "event") for e in edges),
        "has_lifecycle":           a["side_effects"] != "none",   # reliability will author a human-gate lifecycle
        "has_memory":              s.get("memory_hint", False),
        "has_segments":            any(c["kind"] in agent for c in s["components"]),  # evals authors an e2e segment
        "has_saga":                False,   # sagas are authored later, never a floor trigger
        "has_scope":               any(k in agent for k in kind.values()),  # privilege authors scopes
        "has_policyref":           any(is_ag(e["from"]) or is_ag(e["to"]) for e in edges),  # boundary authors validation
    }


def floor_commands(s):
    feats = features_from_scenario(s)
    floor = {c for c, checks in PRIMARY_CHECKS.items() if any(ACTIVATES[k](feats) for k in checks)}
    if s["answers"]["side_effects"] == "irreversible":            # human gate (non-#10)
        floor.add("agentic-reliability")
    if s["answers"]["autonomy"] in ("supervised", "autonomous") and s["answers"]["side_effects"] != "none":
        floor.add("agentic-reliability")                          # kill-switch (non-#10)
    return floor


def rung_relevant(cmd, s):
    a = s["answers"]
    if cmd == "agentic-memory":
        return s.get("memory_hint", False) and not s.get("memory_declared", False)
    if cmd == "agentic-deploy":
        return a.get("greenfield") or a.get("changes_platform") or a.get("deploy_requested")
    return False


def topo_order(included):
    out, seen = [], set()
    while len(out) < len(included):
        for c in COMMANDS:  # stable tie-break
            if c in included and c not in seen and all(d in seen for d in DEPENDS.get(c, [])):
                out.append(c); seen.add(c); break
    return out


def compose(s):
    floor = floor_commands(s)
    rungs = {c for c in COMMANDS if c not in floor and rung_relevant(c, s)}
    inc = floor | rungs
    return {"floor": sorted(floor), "rungs": sorted(rungs), "workflow": topo_order(inc)}
