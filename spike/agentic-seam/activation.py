"""THE single activation source (#10 LLD §6.0).

Both #10's validator dispatch (validator.py) and the Advisor composer (compose.py) import ACTIVATES from
here. There is no second copy — this is the round-7 B1 fix. Each predicate reads `manifest_features`, a plain
dict describing what the manifest contains.
"""

# BLOCKING checks only (check_compensation_gap is advisory → not here; it never gates the floor).
ACTIVATES = {
    "check_classification": lambda f: f["any_agent"] and f["has_interactions"],
    "check_boundary_legs":  lambda f: f["agent_endpoint"],
    "check_topology":       lambda f: f["has_interactions"] or f["orchestration_or_segments"],
    "check_references":     lambda f: f["has_interactions"],
    "check_authorization":  lambda f: f["into_agent"] or f["declares_authorization"],
    "check_capabilities":   lambda f: f["any_agent"],
    "check_scope_grammar":  lambda f: f["has_scope"],
    "check_async":          lambda f: f["any_async"],
    "check_lifecycle":      lambda f: f["has_lifecycle"],
    "check_deep_agent":     lambda f: f["any_deep_agent"],
    "check_memory":         lambda f: f["has_memory"],
    "check_eval_coverage":  lambda f: f["any_agent"] or f["has_segments"],
    "check_saga":           lambda f: f["has_saga"],
    "check_policy_refs":    lambda f: f["has_policyref"],
    "check_observability":  lambda f: f["any_agent"],
}


def features_from_manifest(m):
    """Derive manifest_features from an authored manifest dict — the honest reading of #10 §6.0 predicates."""
    domains = m.get("domains", {})
    inter = m.get("interactions", [])
    agent_kinds = {"simple_agent", "deep_agent"}

    def kind(d):
        return domains.get(d, {}).get("kind")

    def is_agent(d):
        return kind(d) in agent_kinds

    any_scope = any("privilege" in dv.get("identity", {}) for dv in domains.values()) or \
        any(u.get("scopes") for dv in domains.values() for u in dv.get("uses", []))
    any_policyref = any(l.get("validation") for i in inter for l in _legs(i)) or \
        any(s.get("compensation") for sg in m.get("sagas", []) for s in sg.get("steps", [])) or \
        any(w.get("high_stakes_guardrail") for dv in domains.values()
            for w in [dv.get("memory", {}).get("long_term", {})] if w.get("high_stakes_guardrail"))
    return {
        "any_agent":               any(is_agent(d) for d in domains),
        "any_deep_agent":          any(kind(d) == "deep_agent" for d in domains),
        "has_interactions":        len(inter) > 0,
        "orchestration_or_segments": bool(m.get("orchestration")) or bool(m.get("segments")),
        "agent_endpoint":          any(is_agent(i["from"]) or is_agent(i["to"]) for i in inter),
        "into_agent":              any(is_agent(i["to"]) for i in inter),
        "declares_authorization":  any("authorization" in i for i in inter),
        "any_async":               any(i.get("kind") in ("async_task", "event") or "async" in i for i in inter),
        "has_lifecycle":           any("lifecycle" in dv for dv in domains.values()),
        "has_memory":              any("memory" in dv for dv in domains.values()),
        "has_segments":            bool(m.get("segments")),
        "has_saga":                bool(m.get("sagas")),
        "has_scope":               any_scope,
        "has_policyref":           bool(any_policyref),
    }


def _legs(interaction):
    return [interaction[k] for k in ("request", "response", "event") if k in interaction]
