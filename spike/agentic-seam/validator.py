"""A real-but-minimal #10 validator (compound LLD §6). Enough to run the fixtures honestly: each activated
check verifies the REQUIRED fields per §6.2-§6.17 are present + well-formed. If the authored state (via the
writer) omits a field, the matching check fails — which is the executable test of B2 (state sufficiency).
"""
import re
from activation import ACTIVATES, features_from_manifest, _legs

SCOPE_RE = re.compile(r"^[a-z][a-z0-9_-]*:[a-z0-9/_*-]+$")
AGENT = {"simple_agent", "deep_agent"}
REQUIRED_ATTRS = {
    "otel_genai": {"gen_ai.system", "gen_ai.operation.name", "gen_ai.request.model",
                   "gen_ai.usage.input_tokens", "gen_ai.usage.output_tokens"},
    "openinference": {"openinference.span.kind", "llm.model_name",
                      "llm.token_count.prompt", "llm.token_count.completion"},
}


def validate(m, tier, waivers=()):
    """Returns a list of blockers {code, locus}. Empty ⇒ exit 0. Honours manifest-waivers (round-6 B3)."""
    feats = features_from_manifest(m)
    checks = {name: fn for name, fn in _CHECKS.items() if ACTIVATES[name](feats)}
    blockers = []
    for name, fn in checks.items():
        blockers += fn(m, tier)
    waived = {(w["code"], w["locus"]) for w in waivers if tier <= w["tier_limit"]}
    return [b for b in blockers if (b["code"], b["locus"]) not in waived], sorted(checks)


def _domains(m):
    return m.get("domains", {})


def _is_agent(m, d):
    return _domains(m).get(d, {}).get("kind") in AGENT


def _policy_ids(m):
    return {p["id"] for p in m.get("policies", [])}


def _store_ids(m):
    return {s["id"] for s in m.get("stores", [])}


def check_classification(m, tier):
    out = []
    for d, dv in _domains(m).items():
        if "kind" not in dv:
            out.append({"code": "classification_missing", "locus": d})
        elif dv["kind"] in AGENT and not dv.get("kind_rationale"):
            out.append({"code": "kind_rationale_missing", "locus": d})
    return out


def check_boundary_legs(m, tier):
    out = []
    for i in m.get("interactions", []):
        for leg_name in ("request", "response", "event"):
            leg = i.get(leg_name)
            if leg is None:
                continue
            # consumer of this leg:
            consumer = i["to"] if leg_name in ("request", "event") else i["from"]
            source = i["from"] if leg_name in ("request", "event") else i["to"]
            if _is_agent(m, consumer):  # stochastic consumer ⇒ cost + authority bounds
                if "cost_bound" not in leg:
                    out.append({"code": "leg_cost_missing", "locus": i["id"]})
                if "authority_bound" not in leg:
                    out.append({"code": "leg_authority_missing", "locus": i["id"]})
            elif _is_agent(m, source):  # stochastic source → deterministic consumer ⇒ validation
                if "validation" not in leg:
                    out.append({"code": "leg_validation_missing", "locus": i["id"]})
    return out


def check_topology(m, tier):
    out = []
    seen = set()
    ids = {d for d in _domains(m)}
    for i in m.get("interactions", []):
        if i["id"] in seen:
            out.append({"code": "duplicate_interaction_id", "locus": i["id"]})
        seen.add(i["id"])
        if i["from"] not in ids or i["to"] not in ids:
            out.append({"code": "endpoint_not_a_domain", "locus": i["id"]})
    return out


def check_references(m, tier):
    out = []
    for i in m.get("interactions", []):
        fac = i.get("facade")
        if fac and fac not in _domains(m).get(i["to"], {}).get("facade_apis", {}):
            out.append({"code": "facade_unresolved", "locus": i["id"]})
    return out


def check_authorization(m, tier):
    out = []
    for i in m.get("interactions", []):
        if _is_agent(m, i["to"]):
            authz = i.get("authorization")
            if not authz or not authz.get("allowed_callers"):
                out.append({"code": "authorization_missing", "locus": i["id"]})
            else:
                for caller in authz["allowed_callers"]:
                    if "principal" not in _domains(m).get(caller, {}).get("identity", {}):
                        out.append({"code": "caller_not_a_principal", "locus": i["id"]})
    return out


def check_capabilities(m, tier):
    out = []
    for d, dv in _domains(m).items():
        if dv.get("kind") in AGENT:
            if "identity" not in dv:
                out.append({"code": "identity_missing", "locus": d})
            if tier >= 2 and not dv.get("uses"):
                out.append({"code": "uses_missing", "locus": d})
    return out


def check_scope_grammar(m, tier):
    out = []
    scopes = []
    for d, dv in _domains(m).items():
        scopes += dv.get("identity", {}).get("privilege", [])
        for u in dv.get("uses", []):
            scopes += u.get("scopes", [])
    for i in m.get("interactions", []):
        for leg in _legs(i):
            scopes += leg.get("authority_bound", [])
    for sc in scopes:
        if not SCOPE_RE.match(sc):
            out.append({"code": "scope_grammar", "locus": sc})
    return out


def check_async(m, tier):
    out = []
    for i in m.get("interactions", []):
        a = i.get("async")
        if i.get("kind") == "async_task" and a is None:
            out.append({"code": "async_missing", "locus": i["id"]})
        if a:
            if "timeout" not in a:
                out.append({"code": "async_timeout_missing", "locus": i["id"]})
            if a.get("delivery") == "at_least_once" and not a.get("consumer_idempotent"):
                out.append({"code": "alo_not_idempotent", "locus": i["id"]})
            if a.get("delivery") == "at_least_once" and not a.get("dlq") and not a.get("dlq_justification"):
                out.append({"code": "dlq_missing", "locus": i["id"]})
    return out


LIFECYCLE_REQ = ("resumable", "idempotent_resume", "checkpoint", "timeout", "cancellation")


def check_lifecycle(m, tier):
    out = []
    for d, dv in _domains(m).items():
        lc = dv.get("lifecycle")
        if not lc:
            continue
        if lc.get("long_running"):
            for f in ("resumable", "idempotent_resume"):
                if not lc.get(f):
                    out.append({"code": "lifecycle_resume_missing", "locus": d})
            if lc.get("checkpoint") == "durable" and lc.get("checkpoint_store") not in _store_ids(m):
                out.append({"code": "checkpoint_store_unresolved", "locus": d})
        if lc.get("human_gate") and not lc.get("human_gate_pause"):
            out.append({"code": "human_gate_pause_missing", "locus": d})
        if "cancellation" not in lc:
            out.append({"code": "cancellation_missing", "locus": d})
    return out


def check_deep_agent(m, tier):
    out = []
    for d, dv in _domains(m).items():
        if dv.get("kind") == "deep_agent":
            da = dv.get("deep_agent")
            if not da:
                out.append({"code": "deep_agent_block_missing", "locus": d})
                continue
            for f in ("planner", "subagents", "gates", "guardrails"):
                if not da.get(f):
                    out.append({"code": f"deep_agent_{f}_missing", "locus": d})
            if da.get("context_isolation") is not True:
                out.append({"code": "context_isolation_missing", "locus": d})
    return out


def check_memory(m, tier):
    out = []
    for d, dv in _domains(m).items():
        mem = dv.get("memory")
        if not mem:
            continue
        lt = mem.get("long_term")
        if lt:
            for f in ("owner", "store", "durability", "retrieval", "scope", "pii"):
                if f not in lt:
                    out.append({"code": f"memory_{f}_missing", "locus": d})
            if lt.get("pii") == "none" and not lt.get("pii_justification"):
                out.append({"code": "pii_justification_missing", "locus": d})
            if lt.get("store") not in _store_ids(m):
                out.append({"code": "memory_store_unresolved", "locus": d})
    return out


def check_eval_coverage(m, tier):
    out = []
    specs = {(e["target_type"], e["target_id"]) for e in m.get("evals", [])}
    for d, dv in _domains(m).items():
        if dv.get("kind") in AGENT and ("component", d) not in specs:
            out.append({"code": "eval_uncovered_agent", "locus": d})
    n_components = len(_domains(m))
    e2e = [s for s in m.get("segments", []) if s.get("e2e")]
    if n_components >= 2 and not e2e:
        out.append({"code": "no_e2e_segment", "locus": "system"})
    for e in m.get("evals", []):
        if tier >= 2 and e.get("approval", {}).get("decision") != "approved":
            out.append({"code": "eval_not_approved", "locus": e["target_id"]})
    return out


def check_saga(m, tier):
    out = []
    for sg in m.get("sagas", []):
        if sg.get("order") != "sequential":
            out.append({"code": "saga_order_invalid", "locus": sg["id"]})
        for st in sg.get("steps", []):
            if st.get("compensation") not in _policy_ids(m):
                out.append({"code": "compensation_unresolved", "locus": sg["id"]})
            if not st.get("compensation_idempotent"):
                out.append({"code": "compensation_not_idempotent", "locus": sg["id"]})
    return out


def check_policy_refs(m, tier):
    out = []
    ids = _policy_ids(m)
    refs = []
    for i in m.get("interactions", []):
        for leg in _legs(i):
            if leg.get("validation"):
                refs.append((leg["validation"], i["id"]))
    for sg in m.get("sagas", []):
        for st in sg.get("steps", []):
            if st.get("compensation"):
                refs.append((st["compensation"], sg["id"]))
    for ref, locus in refs:
        if ref not in ids:
            out.append({"code": "policy_ref_unresolved", "locus": locus})
    return out


def _resolvable(ref, m):
    kind, _, rest = ref.partition(":")
    if kind == "domain":
        return rest in _domains(m)
    if kind == "facade":
        d, _, f = rest.partition(".")
        return f in _domains(m).get(d, {}).get("facade_apis", {})
    if kind == "artifact":
        return bool(rest)  # spike: a path string stands in for "exists"
    if kind == "service":
        return rest in {s["id"] for s in m.get("approved_services", [])}
    return False


def check_observability(m, tier):
    out = []
    o = m.get("observability")
    if not o:
        return [{"code": "observability_missing", "locus": "system"}]
    tr = o.get("tracing", {})
    conv = tr.get("convention")
    if conv not in REQUIRED_ATTRS:
        out.append({"code": "observability_convention", "locus": "system"})
    elif not REQUIRED_ATTRS[conv] <= set(tr.get("attributes", [])):
        out.append({"code": "observability_attrs", "locus": "system"})
    agent_hops = [i["id"] for i in m.get("interactions", []) if _is_agent(m, i["from"]) or _is_agent(m, i["to"])]
    if not set(agent_hops) <= set(tr.get("hops", [])):
        out.append({"code": "observability_hop_untraced", "locus": "system"})
    if o.get("cost_budget", {}).get("limit", 0) <= 0:
        out.append({"code": "observability_cost_budget", "locus": "system"})
    ec = o.get("eval_console", {})
    access_ok = ec.get("access") in (("report", "existing_surface", "console") if tier <= 1 else ("console",))
    if not access_ok:
        out.append({"code": "observability_console_access", "locus": "system"})
    if not ec.get("owner") or not _resolvable(ec.get("ref", ""), m):
        out.append({"code": "observability_console_ref", "locus": "system"})
    return out


_CHECKS = {
    "check_classification": check_classification, "check_boundary_legs": check_boundary_legs,
    "check_topology": check_topology, "check_references": check_references,
    "check_authorization": check_authorization, "check_capabilities": check_capabilities,
    "check_scope_grammar": check_scope_grammar, "check_async": check_async,
    "check_lifecycle": check_lifecycle, "check_deep_agent": check_deep_agent,
    "check_memory": check_memory, "check_eval_coverage": check_eval_coverage,
    "check_saga": check_saga, "check_policy_refs": check_policy_refs,
    "check_observability": check_observability,
}
