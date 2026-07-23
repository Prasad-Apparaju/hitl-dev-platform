"""LOW / HIGH / DEEP canonical states — scenario + FULL authored.* per the round-7 §7.1 schema.
If the schema is missing a field #10 needs, write_manifest → validate will surface it (the B2 test).
"""

OTEL = ["gen_ai.system", "gen_ai.operation.name", "gen_ai.request.model",
        "gen_ai.usage.input_tokens", "gen_ai.usage.output_tokens"]


def _obs(hops):
    # tracing is NESTED (matches #10 §4.3), not flat — the shape mismatch the spike caught
    return {"tracing": {"convention": "otel_genai", "hops": hops, "attributes": OTEL},
            "cost_budget": {"limit": 100000, "unit": "tokens"},
            "eval_console": {"access": "report", "owner": "pm", "ref": "artifact:docs/eval-console.md"}}


def _ident(cid):
    return {"component_id": cid, "principal": f"svc:{cid}", "privilege": [f"act:{cid}/*"],
            "uses": [{"capability": "model", "scopes": [f"invoke:model/{cid}"]}]}


def _eval(cid):
    return {"target_type": "component", "target_id": cid, "kind": "eval",
            "spec_path": f"evals/{cid}.yaml", "approval": {"reviewer": "pm", "date": "2026-07-23", "decision": "approved"}}


# ---- LOW: 2 agents, read-only, internal, Tier 1 ------------------------------------------------
LOW = {
    "tier": 1,
    "components": [{"id": "a1", "kind": "simple_agent", "kind_rationale": "bounded intake"},
                   {"id": "a2", "kind": "simple_agent", "kind_rationale": "bounded resolver"}],
    "edges": [{"id": "e1", "from": "a1", "to": "a2", "kind": "sync_call"}],
    "answers": {"stakes": "internal", "side_effects": "none", "data": "none",
                "autonomy": "assisted", "scale": "small", "greenfield": True},
    "authored": {
        "facades": [{"id": "f1", "on": "a2", "name": "resolve", "signature": "Req->Resp", "blurb": "resolve a case",
                     "mutations": [], "preconditions": ["valid case"], "error_modes": ["not_found"]}],
        "legs": [{"edge_id": "e1", "leg": "request", "cost_bound": "budget:e1", "authority_bound": ["act:a2/resolve"]}],
        "authorizations": [{"edge_id": "e1", "allowed_callers": ["a1"], "credential_mode": "jit"}],
        "identities": [_ident("a1"), _ident("a2")],
        "observability": _obs(["e1"]),
        "evals": [_eval("a1"), _eval("a2")],
        "segments": [{"id": "seg1", "path": ["e1"], "e2e": True,
                      "evals": {"spec": "evals/e2e.yaml"}}],
    },
}

# ---- HIGH: 4 components (2 agents), irreversible, PII, supervised, async edge, Tier 2 ----------
HIGH = {
    "tier": 2,
    "components": [{"id": "a1", "kind": "simple_agent", "kind_rationale": "intake"},
                   {"id": "a2", "kind": "simple_agent", "kind_rationale": "resolver"},
                   {"id": "s", "kind": "deterministic", "kind_rationale": "account service"},
                   {"id": "d", "kind": "deterministic", "kind_rationale": "ledger"}],
    "edges": [{"id": "e1", "from": "a1", "to": "s", "kind": "sync_call"},
              {"id": "e2", "from": "a1", "to": "a2", "kind": "sync_call"},
              {"id": "e3", "from": "a2", "to": "d", "kind": "async_task"}],
    "answers": {"stakes": "customer_facing", "side_effects": "irreversible", "data": "pii",
                "autonomy": "supervised", "scale": "small", "greenfield": True},
    "authored": {
        "facades": [
            {"id": "f_s", "on": "s", "name": "lookup", "signature": "Acc->Bal", "blurb": "account lookup",
             "mutations": [], "preconditions": [], "error_modes": ["not_found"]},
            {"id": "f_a2", "on": "a2", "name": "resolve", "signature": "Req->Resp", "blurb": "resolve",
             "mutations": [], "preconditions": [], "error_modes": []},
            {"id": "f_d", "on": "d", "name": "post", "signature": "Txn->Ack", "blurb": "post to ledger",
             "mutations": ["ledger"], "preconditions": [], "error_modes": ["dup"]}],
        "legs": [
            {"edge_id": "e1", "leg": "response", "validation": "val:e1"},   # s(det)→a1(agent)? consumer a1 is agent ⇒ cost/authority
            {"edge_id": "e1", "leg": "request", "validation": "val:e1req"},  # a1(agent)→s(det) ⇒ validation
            {"edge_id": "e2", "leg": "request", "cost_bound": "budget:e2", "authority_bound": ["act:a2/resolve"]},
            {"edge_id": "e3", "leg": "request", "validation": "val:e3"}],    # a2(agent)→d(det) ⇒ validation
        "authorizations": [{"edge_id": "e2", "allowed_callers": ["a1"], "credential_mode": "jit"}],
        "identities": [_ident("a1"), _ident("a2")],
        "async": [{"edge_id": "e3", "delivery": "at_least_once", "consumer_idempotent": True,
                   "idempotency_key": "txn.id", "dlq": "dlq:e3", "timeout": "30s"}],
        "lifecycle": [{"component_id": "a2", "long_running": False, "human_gate": True,
                       "human_gate_pause": True, "cancellation": "cooperative"}],
        "observability": {**_obs(["e1", "e2", "e3"]),
                          "eval_console": {"access": "console", "owner": "pm", "ref": "domain:a2"}},  # Tier 2 ⇒ console
        "evals": [_eval("a1"), _eval("a2")],
        "segments": [{"id": "seg1", "path": ["e1", "e2", "e3"], "e2e": True, "evals": {"spec": "evals/e2e.yaml"}}],
        "policies": [{"id": "val:e1", "kind": "schema"}, {"id": "val:e1req", "kind": "schema"},
                     {"id": "val:e3", "kind": "schema"}],
    },
}

# fix HIGH leg e1: the correct legs — a1→s request(validation), response back to a1(agent) cost/authority
HIGH["authored"]["legs"] = [
    {"edge_id": "e1", "leg": "request", "validation": "val:e1req"},                       # a1(agent)→s(det): validate agent output
    {"edge_id": "e1", "leg": "response", "cost_bound": "budget:e1", "authority_bound": ["act:a1/read"]},  # s(det)→a1(agent): bound
    {"edge_id": "e2", "leg": "request", "cost_bound": "budget:e2", "authority_bound": ["act:a2/resolve"]},  # a1→a2(agent): bound
    {"edge_id": "e3", "leg": "request", "validation": "val:e3"},                          # a2(agent)→d(det): validate
]
HIGH["authored"]["policies"] = [{"id": "val:e1req", "kind": "schema"}, {"id": "val:e3", "kind": "schema"}]

# ---- DEEP: LOW but a1 is a deep_agent ----------------------------------------------------------
import copy
DEEP = copy.deepcopy(LOW)
DEEP["components"][0]["kind"] = "deep_agent"
DEEP["authored"]["deep_agents"] = [{"component_id": "a1", "planner": "plan", "subagents": ["a2"],
                                    "context_isolation": True, "gates": ["g:review"], "guardrails": ["gd:safe"]}]
DEEP["authored"].setdefault("policies", [])
