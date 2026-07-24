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
  wave 3  check_capabilities, check_boundary_legs, check_authorization, check_policy_refs
  wave 4  check_async, check_memory, check_lifecycle, check_deep_agent, check_saga,
          check_compensation_gap (advisory)
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
# Scope containment helpers (§6.17.1, verbatim semantics) + wave 3 checks
# ══════════════════════════════════════════════════════════════════════════════
def canon(s):            return str(s).strip().lower()
def _split(scope):       return scope.split(":", 1)

def resource_covers(ceiling_res, use_res):
    if ceiling_res == "*":
        return True
    if ceiling_res.endswith("/*"):
        base = ceiling_res[:-2]
        return use_res == base or use_res.startswith(base + "/")
    return ceiling_res == use_res

def scope_in_ceiling(scope, ceiling):
    if ":" not in scope:
        return False
    act, res = _split(scope)
    for c in ceiling:
        if ":" not in c:
            continue
        ca, cr = _split(c)
        if ca == act and resource_covers(cr, res):
            return True
    return False

def use_scopes(u):
    out = []
    for op in u.get("operations", []):
        for res in (u.get("resources") or ["*"]):
            out.append(canon(f"{op}:{res}"))
    return out

def _privilege(m, dname):
    return {canon(x) for x in ((domains(m).get(dname) or {}).get("identity") or {}).get("privilege", [])}


def check_capabilities(m, reg, tier):
    """§6.2: capability-in-registry, ceiling containment, over/under privilege
    (mutual wildcard coverage), Tier2+ agent-with-identity-but-no-uses."""
    out = []
    regfile = reg.get("capabilities")
    if regfile is None:
        return []  # registry error already recorded
    caps = regfile.get("capabilities") or {}
    for name, d in domains(m).items():
        uses = d.get("uses") or []
        granted = _privilege(m, name)
        needed = set()
        for u in uses:
            cap = caps.get(u.get("capability"))
            if not cap:
                out.append(block(name, "capability_not_in_registry",
                                 f"{name}: capability '{u.get('capability')}' not in approved-capabilities.yaml"))
                continue
            for sc in use_scopes(u):
                if not scope_in_ceiling(sc, cap.get("ceiling", [])):
                    out.append(block(name, "ceiling_violation",
                                     f"{name}: scope '{sc}' exceeds the ceiling of '{u['capability']}'"))
                needed.add(sc)
        for g in granted:
            if not scope_in_ceiling(g, list(needed)):
                out.append(block(name, "over_privilege", f"{name}: granted scope '{g}' exceeds what is needed"))
        for n in needed:
            if not scope_in_ceiling(n, list(granted)):
                out.append(block(name, "under_privilege", f"{name}: needed scope '{n}' is not granted"))
        if tier >= 2 and d.get("kind") in AGENT_KINDS and d.get("identity") and not uses:
            out.append(block(name, "agent_unscoped",
                             f"{name}: a Tier {tier} agent with identity must scope its capabilities via `uses`"))
    return out


def check_boundary_legs(m, reg, tier):
    """§6.3/§2.2: per leg, from (source,consumer) apply the boundary rule; a
    required leg must be present; agent-consumer needs cost+authority (⊆ its
    privilege); stochastic-source→deterministic-consumer needs validation."""
    out = []
    for i in interactions(m):
        iid = i.get("id", "?")
        k = i.get("kind")
        frm, to = i.get("from"), i.get("to")
        legs = ([("request", frm, to), ("response", to, frm)]
                if k in ("sync_call", "async_task")
                else [("request", frm, to)] if k == "event" else [])
        for leg_name, source, consumer in legs:
            leg = i.get(leg_name)
            consumer_agent = is_agent(m, consumer)
            source_agent = is_agent(m, source)
            required = consumer_agent or (source_agent and not consumer_agent)
            if required and leg is None:
                out.append(block(iid, "leg_missing",
                                 f"{iid}.{leg_name}: required control leg (source {source} -> consumer {consumer}) is absent"))
                continue
            if consumer_agent:
                if leg.get("cost_bound") is None:
                    out.append(block(iid, "boundary_cost_missing", f"{iid}.{leg_name}: agent consumer needs cost_bound"))
                ab = leg.get("authority_bound")
                if ab is None:
                    out.append(block(iid, "boundary_authority_missing", f"{iid}.{leg_name}: agent consumer needs authority_bound"))
                else:
                    priv = _privilege(m, consumer)
                    for sc in ab:
                        if not scope_in_ceiling(canon(sc), list(priv)):
                            out.append(block(iid, "authority_exceeds_privilege",
                                             f"{iid}.{leg_name}: authority '{sc}' ⊄ {consumer}.identity.privilege"))
            elif source_agent and not consumer_agent:
                if leg.get("validation") is None:
                    out.append(block(iid, "validation_missing",
                                     f"{iid}.{leg_name}: stochastic source -> deterministic consumer needs validation"))
    return out


def check_authorization(m, reg, tier):
    """§6.4: interaction into an agent needs allowed_callers incl. the caller;
    each allowed_caller is a domain with identity.principal; static/none justified."""
    out = []
    dmap = domains(m)
    for i in interactions(m):
        iid, to, frm = i.get("id", "?"), i.get("to"), i.get("from")
        auth = i.get("authorization")
        into_agent = is_agent(m, to)
        if into_agent and not (auth and auth.get("allowed_callers")):
            out.append(block(iid, "authorization_missing",
                             f"{iid}: interaction into agent '{to}' needs authorization.allowed_callers"))
        if auth:
            ac = auth.get("allowed_callers") or []
            if into_agent and frm not in ac:
                out.append(block(iid, "caller_not_allowed", f"{iid}: caller '{frm}' not in allowed_callers of '{to}'"))
            for c in ac:
                principal = ((dmap.get(c) or {}).get("identity") or {}).get("principal")
                if not principal:
                    out.append(block(iid, "caller_no_identity", f"{iid}: allowed_caller '{c}' has no identity.principal"))
            cm = auth.get("credential_mode")
            if cm in ("static", "none") and not (auth.get("credential_justification") or "").strip():
                out.append(block(iid, "credential_unjustified", f"{iid}: credential_mode '{cm}' needs credential_justification"))
    return out


def check_policy_refs(m, reg, tier):
    """§6.8: every PolicyRef resolves + fits its expected kind; QuantPolicy limit>0/unit valid."""
    out = []
    regfile = reg.get("policies")
    if regfile is None:
        return []
    pols = regfile.get("policies") or {}

    def ref(r, locus, expect):
        if not r or canon(r) in ("todo", "none", ""):
            out.append(block(locus, "policy_ref_empty", f"{locus}: empty/TODO policy ref"))
            return
        p = pols.get(r)
        if not p:
            out.append(block(locus, "policy_ref_unresolved", f"{locus}: policy '{r}' not in policies.yaml"))
            return
        if expect and p.get("kind") not in expect:
            out.append(block(locus, "policy_kind_mismatch",
                             f"{locus}: policy '{r}' kind '{p.get('kind')}' not in {sorted(expect)}"))

    def quant(qp, locus):
        if qp is None:
            return
        if not (isinstance(qp.get("limit"), (int, float)) and not isinstance(qp.get("limit"), bool) and qp["limit"] > 0):
            out.append(block(locus, "quantpolicy_limit", f"{locus}: QuantPolicy limit must be > 0"))
        if qp.get("unit") not in ("tokens", "calls", "fanout"):
            out.append(block(locus, "quantpolicy_unit", f"{locus}: QuantPolicy unit invalid"))

    for i in interactions(m):
        iid = i.get("id", "?")
        for leg in ("request", "response"):
            L = i.get(leg) or {}
            if L.get("validation") is not None:
                ref(L["validation"], iid, {"schema", "guardrail"})
            quant(L.get("cost_bound"), iid)
    for s in sagas(m):
        for st in s.get("steps", []):
            ref(st.get("compensation"), s.get("id", "?"), {"action"})
    for name, d in domains(m).items():
        da = d.get("deep_agent") or {}
        for r in (da.get("gates") or []) + (da.get("guardrails") or []):
            ref(r, name, {"guardrail"})
        hsg = ((d.get("memory") or {}).get("long_term") or {}).get("high_stakes_guardrail")
        if hsg is not None:
            ref(hsg, name, {"guardrail"})
    ob = m.get("observability")
    if ob:
        quant(ob.get("cost_budget"), "system:observability")
    return out


def _has_policy_or_quant(m):
    for i in interactions(m):
        for leg in ("request", "response"):
            L = i.get(leg) or {}
            if L.get("validation") is not None or L.get("cost_bound") is not None:
                return True
    if sagas(m):
        return True
    for d in domains(m).values():
        da = d.get("deep_agent") or {}
        if da.get("gates") or da.get("guardrails"):
            return True
        if ((d.get("memory") or {}).get("long_term") or {}).get("high_stakes_guardrail"):
            return True
    return bool((m.get("observability") or {}).get("cost_budget"))


def _declared_scopes(d):
    s = set()
    for u in d.get("uses") or []:
        s |= set(use_scopes(u))
    return s

def _domain_side_effecting(m, name):
    return any(i.get("from") == name and i.get("side_effecting") for i in interactions(m))


# ══════════════════════════════════════════════════════════════════════════════
# Wave 4 — reliability / state
# ══════════════════════════════════════════════════════════════════════════════
def check_async(m, reg, tier):
    """§6.7: async-block reliability contract (delivery/idempotency/dlq/retry/timeout).
    Presence-by-kind (async on sync_call, async_task w/o async) is check_topology."""
    out = []
    for i in interactions(m):
        a = i.get("async")
        if a is None:
            continue
        iid = i.get("id", "?")
        to = a.get("timeout")
        if not to or not DURATION_RE.match(str(to)):
            out.append(block(iid, "async_timeout_missing", f"{iid}: async.timeout must be a positive duration"))
        if a.get("delivery") == "at_least_once":
            if not a.get("consumer_idempotent") or not a.get("idempotency_key"):
                out.append(block(iid, "async_not_idempotent",
                                 f"{iid}: at_least_once requires consumer_idempotent + idempotency_key"))
            if not a.get("dlq") and not (a.get("dlq_justification") or "").strip():
                out.append(block(iid, "async_dlq_missing", f"{iid}: at_least_once requires dlq (or a dlq_justification)"))
        if a.get("retry") is not None and a.get("delivery") == "at_most_once":
            out.append(block(iid, "async_retry_forbidden", f"{iid}: retry is forbidden with delivery at_most_once"))
    return out


def check_memory(m, reg, tier):
    """§6.11: long_term completeness, store/shared resolution, PII, high-stakes
    guardrail+provenance, and read/write ⇄ uses reconciliation (§3.1)."""
    out = []
    stores = (reg.get("stores") or {}).get("stores") or {}
    for name, d in domains(m).items():
        mem = d.get("memory")
        if not mem:
            continue
        st = mem.get("short_term")
        if st and st.get("strategy") not in (None, "none") and not st.get("budget_tokens"):
            out.append(block(name, "memory_budget_missing", f"{name}: short_term needs budget_tokens unless strategy==none"))
        lt = mem.get("long_term")
        if not lt:
            continue
        for req in ("owner", "store", "durability", "retrieval", "scope", "pii"):
            if lt.get(req) in (None, ""):
                out.append(block(name, "memory_field_missing", f"{name}: long_term.{req} is required"))
        if lt.get("pii") == "none" and not (lt.get("pii_justification") or "").strip():
            out.append(block(name, "memory_pii_unjustified", f"{name}: long_term.pii 'none' needs pii_justification"))
        store = lt.get("store")
        if store and (stores.get(store) or {}).get("durability") != "durable":
            out.append(block(name, "memory_store_unresolved", f"{name}: store '{store}' must resolve to a durable store"))
        scope, ss = lt.get("scope"), lt.get("shared_store")
        if scope == "shared":
            if not ss:
                out.append(block(name, "memory_shared_store_missing", f"{name}: scope 'shared' needs shared_store"))
            elif not (stores.get(ss) or {}).get("shared"):
                out.append(block(name, "memory_shared_store_invalid", f"{name}: shared_store '{ss}' must be shared:true"))
        if scope == "isolated" and ss:
            out.append(block(name, "memory_shared_on_isolated", f"{name}: shared_store set with scope 'isolated'"))
        for w in lt.get("writes", []):
            if w.get("high_stakes"):
                if not lt.get("high_stakes_guardrail"):
                    out.append(block(name, "memory_high_stakes_guardrail_missing", f"{name}: high_stakes write needs high_stakes_guardrail"))
                if not (w.get("provenance") or "").strip():
                    out.append(block(name, "memory_provenance_missing", f"{name}: high_stakes write needs provenance"))
        declared = _declared_scopes(d)
        for r in lt.get("reads", []):
            if canon(f"read:{r.get('resource')}") not in declared:
                out.append(block(name, "memory_use_unreconciled", f"{name}: memory read '{r.get('resource')}' has no matching uses scope"))
        for w in lt.get("writes", []):
            if canon(f"write:{w.get('resource')}") not in declared:
                out.append(block(name, "memory_use_unreconciled", f"{name}: memory write '{w.get('resource')}' has no matching uses scope"))
    return out


def check_lifecycle(m, reg, tier):
    """§6.10: long_running completeness, durable checkpoint store, resumable side-effect
    key, human-gate pause."""
    out = []
    stores = (reg.get("stores") or {}).get("stores") or {}
    for name, d in domains(m).items():
        lc = d.get("lifecycle")
        if not lc:
            continue
        if lc.get("long_running"):
            if lc.get("resumable") is not True:
                out.append(block(name, "lifecycle_not_resumable", f"{name}: long_running requires resumable:true"))
            if lc.get("idempotent_resume") is not True:
                out.append(block(name, "lifecycle_not_idempotent_resume", f"{name}: long_running requires idempotent_resume:true"))
            if lc.get("checkpoint") == "none":
                out.append(block(name, "lifecycle_checkpoint_none", f"{name}: long_running requires a checkpoint"))
            if not lc.get("resume_cursor"):
                out.append(block(name, "lifecycle_resume_cursor_missing", f"{name}: long_running requires resume_cursor"))
            to = lc.get("timeout")
            if not to or not DURATION_RE.match(str(to)):
                out.append(block(name, "lifecycle_timeout_missing", f"{name}: long_running requires a positive timeout"))
            if not lc.get("cancellation"):
                out.append(block(name, "lifecycle_cancellation_missing", f"{name}: long_running requires cancellation"))
        if lc.get("checkpoint") == "durable":
            cs = lc.get("checkpoint_store")
            if not cs or (stores.get(cs) or {}).get("durability") != "durable":
                out.append(block(name, "lifecycle_checkpoint_store_invalid", f"{name}: checkpoint_store must resolve to a durable store"))
        if lc.get("resumable") and _domain_side_effecting(m, name) and not lc.get("side_effect_key"):
            out.append(block(name, "lifecycle_side_effect_key_missing", f"{name}: resumable + side-effecting needs side_effect_key"))
        if lc.get("human_gate") and lc.get("human_gate_pause") is not True:
            out.append(block(name, "lifecycle_human_gate_pause_missing", f"{name}: human_gate requires human_gate_pause:true"))
    return out


def check_deep_agent(m, reg, tier):
    """§6.9: deep_agent structure completeness + references; block on non-deep kind."""
    out = []
    dset = set(domains(m))
    for name, d in domains(m).items():
        da = d.get("deep_agent")
        if d.get("kind") == "deep_agent":
            if not da:
                out.append(block(name, "deep_agent_missing", f"{name}: kind deep_agent requires a deep_agent block"))
                continue
            lt = (d.get("memory") or {}).get("long_term")
            if not lt:
                out.append(block(name, "deep_agent_memory_missing", f"{name}: deep agent requires memory.long_term"))
            elif lt.get("retrieval") not in ("filesystem", "semantic"):
                out.append(block(name, "deep_agent_retrieval_invalid", f"{name}: deep agent memory retrieval must be filesystem|semantic"))
            for f in ("planner", "subagents", "gates", "guardrails"):
                if not da.get(f):
                    out.append(block(name, "deep_agent_incomplete", f"{name}: deep_agent.{f} is required and non-empty"))
            if da.get("context_isolation") is not True:
                out.append(block(name, "deep_agent_context_isolation", f"{name}: deep_agent.context_isolation must be true"))
            if da.get("planner") and da["planner"] not in dset:
                out.append(block(name, "deep_agent_ref_unknown", f"{name}: planner '{da['planner']}' is not a declared domain"))
            for sa in da.get("subagents", []):
                if sa not in dset:
                    out.append(block(name, "deep_agent_ref_unknown", f"{name}: subagent '{sa}' is not a declared domain"))
        elif da is not None:
            out.append(block(name, "deep_agent_on_non_deep", f"{name}: deep_agent block on a non-deep kind"))
    return out


def check_saga(m, reg, tier):
    """§6.14: declared-saga well-formedness (steps side-effecting+declared,
    compensation→action, idempotent, no overlap, sequential order)."""
    out = []
    pols = (reg.get("policies") or {}).get("policies") or {}
    by_id = {i.get("id"): i for i in interactions(m)}
    coverage = {}
    for s in sagas(m):
        sid = s.get("id", "?")
        if s.get("order") != "sequential":
            out.append(block(sid, "saga_order_invalid", f"saga '{sid}': core supports order 'sequential' only"))
        for st in s.get("steps", []):
            iid = st.get("interaction_id")
            i = by_id.get(iid)
            if not i:
                out.append(block(sid, "saga_step_unknown", f"saga '{sid}' step '{iid}' is not a declared interaction"))
            elif not i.get("side_effecting"):
                out.append(block(sid, "saga_step_not_side_effecting", f"saga '{sid}' step '{iid}' is not side-effecting"))
            comp = st.get("compensation")
            p = pols.get(comp)
            if not p or p.get("kind") != "action":
                out.append(block(sid, "saga_compensation_invalid", f"saga '{sid}' compensation '{comp}' must resolve to an action policy"))
            if st.get("compensation_idempotent") is not True:
                out.append(block(sid, "saga_compensation_not_idempotent", f"saga '{sid}' step '{iid}' compensation must be idempotent"))
            coverage.setdefault(iid, []).append(sid)
    for iid, owners in coverage.items():
        if len(owners) > 1:
            out.append(block(owners[0], "saga_overlap", f"interaction '{iid}' is covered by multiple sagas {owners}"))
    return out


def check_compensation_gap(m, reg, tier):
    """§6.16 ADVISORY (warning, never blocks): a declared segment with ≥2
    side-effecting agent/async steps (or transactional) not covered by a saga."""
    out = []
    by_id = {i.get("id"): i for i in interactions(m)}
    covered = {st.get("interaction_id") for s in sagas(m) for st in s.get("steps", [])}
    for seg in segments(m):
        se = []
        for iid in seg.get("path", []):
            i = by_id.get(iid)
            if i and i.get("side_effecting") and (is_agent(m, i.get("from")) or is_agent(m, i.get("to"))
                                                  or i.get("kind") in ("async_task", "event")):
                se.append(iid)
        uncovered = [iid for iid in se if iid not in covered]
        if uncovered and (seg.get("transactional") or len(se) >= 2):
            out.append(warn(seg.get("id", "?"), "compensation_gap",
                            f"segment '{seg.get('id')}' has side-effecting steps {uncovered} with no covering saga — "
                            f"handle rollback deliberately or declare a saga (§4.2, core does not enforce distributed compensation)"))
    return out


# ══════════════════════════════════════════════════════════════════════════════
# Wave 5 — coverage / floor
# ══════════════════════════════════════════════════════════════════════════════
def _eval_projection(m):
    rows = []
    for name, d in domains(m).items():
        sp = (d.get("evals") or {}).get("spec")
        if sp:
            rows.append(("component", name, sp))
    for i in interactions(m):
        sp = (i.get("evals") or {}).get("spec")
        if sp:
            rows.append(("interaction", i.get("id"), sp))
    for s in segments(m):
        sp = (s.get("evals") or {}).get("spec")
        if sp:
            rows.append(("segment", s.get("id"), sp))
    return rows


def _eval_waived(t, i, waivers, tier, today):
    for w in waivers:
        if w.get("target_type") == t and w.get("target_id") == i \
           and tier <= int(w.get("tier_limit", -1)) and _date(w["revisit"]) >= today:
            return True
    return False


def check_eval_coverage(m, reg, tier):
    """§6.12: mandatory targets = every agent domain + one e2e segment. Each needs an
    index row (a projection of inline evals.spec) or an unlapsed waiver; at Tier2+ the
    spec's approval.decision must be `approved`. Result ingestion is #42, not here."""
    import datetime
    out = []
    idx = reg.get("evals_index") or {}
    wv = reg.get("evals_waivers") or {}
    if idx is None or wv is None:
        return out
    index_rows = {(r.get("target_type"), r.get("target_id")): r.get("spec_path") for r in (idx.get("rows") or [])}
    waivers = wv.get("waivers") or []

    proj = {(t, i): sp for (t, i, sp) in _eval_projection(m)}
    if proj != index_rows:
        out.append(block("system:evals", "eval_index_mismatch",
                         "evals/index.yaml differs from the inline evals.spec projection (regenerate)"))

    mandatory = [("component", n) for n, d in domains(m).items() if d.get("kind") in AGENT_KINDS]
    e2e = [("segment", s.get("id")) for s in segments(m) if s.get("e2e")]
    if len(domains(m)) >= 2 and not e2e:
        out.append(block("system:evals", "e2e_missing", "a multi-component agentic system needs one e2e:true segment"))
    mandatory += e2e[:1]

    today = datetime.date.today()
    for (t, i) in mandatory:
        if _eval_waived(t, i, waivers, tier, today):
            continue
        sp = index_rows.get((t, i))
        if not sp:
            out.append(block(str(i), "eval_coverage_missing", f"{t} '{i}' has no eval spec in the index and no unlapsed waiver"))
            continue
        if tier >= 2:
            spec = _load_yaml(os.path.join(reg.root, sp))
            if spec is None or (spec.get("approval") or {}).get("decision") != "approved":
                out.append(block(str(i), "eval_not_approved", f"{t} '{i}' eval spec approval.decision != approved (required at Tier {tier})"))
    return out


REQUIRED_ATTRS = {
    "otel_genai": {"gen_ai.system", "gen_ai.operation.name", "gen_ai.request.model",
                   "gen_ai.usage.input_tokens", "gen_ai.usage.output_tokens"},
    "openinference": {"openinference.span.kind", "llm.model_name",
                      "llm.token_count.prompt", "llm.token_count.completion"},
}

def _access_ok(access, tier):
    if tier <= 1:
        return access in ("report", "existing_surface", "console")
    return access == "console"

def _resolves(ref, m, root):
    if not ref or ":" not in str(ref):
        return False
    kind, val = str(ref).split(":", 1)
    if kind == "domain":
        return val in domains(m)
    if kind == "facade":
        if ":" not in val:
            return False
        d, api = val.split(":", 1)
        return d in domains(m) and api in ((domains(m).get(d) or {}).get("facade_apis") or {})
    if kind == "service":
        return bool(val.strip())            # an approved-service registry id (registry check out of core here)
    if kind == "artifact":
        return os.path.exists(os.path.join(root, val))
    return False


def check_observability(m, reg, tier):
    """§6.17 FLOOR GATE: an agentic system must declare a real, tier-scaled
    observability block — convention-required attributes, agent-hop tracing, a
    positive cost budget, and a resolvable, tier-appropriate PM eval-console."""
    out = []
    o = m.get("observability")
    if not o:
        out.append(block("system:observability", "observability_missing",
                         "an agentic system must declare `observability` (floor gate, hard directive)"))
        return out
    tr = o.get("tracing") or {}
    conv = tr.get("convention")
    if conv not in REQUIRED_ATTRS:
        out.append(block("system:observability", "observability_convention", "tracing.convention must be otel_genai|openinference"))
    elif not set(tr.get("attributes") or []) >= REQUIRED_ATTRS[conv]:
        missing = REQUIRED_ATTRS[conv] - set(tr.get("attributes") or [])
        out.append(block("system:observability", "observability_attributes",
                         f"tracing.attributes must ⊇ the required {conv} set (missing {sorted(missing)})"))
    agent_hops = {i.get("id") for i in interactions(m) if is_agent(m, i.get("from")) or is_agent(m, i.get("to"))}
    if not set(tr.get("hops") or []) >= agent_hops:
        out.append(block("system:observability", "observability_hops",
                         "tracing.hops must ⊇ every agent-endpoint interaction"))
    cb = o.get("cost_budget")
    if not (cb and isinstance(cb.get("limit"), (int, float)) and not isinstance(cb.get("limit"), bool) and cb["limit"] > 0):
        out.append(block("system:observability", "observability_cost_budget", "observability.cost_budget.limit must be > 0"))
    ec = o.get("eval_console")
    if not ec:
        out.append(block("system:observability", "eval_console_missing", "observability requires an eval_console"))
        return out
    if not (ec.get("owner") or "").strip():
        out.append(block("system:observability", "eval_console_owner", "eval_console.owner is required"))
    if not _access_ok(ec.get("access"), tier):
        out.append(block("system:observability", "eval_console_access",
                         f"Tier {tier} requires eval_console.access 'console' (got '{ec.get('access')}')"))
    if not _resolves(ec.get("ref"), m, reg.root):
        out.append(block("system:observability", "eval_console_ref_unresolved",
                         f"eval_console.ref '{ec.get('ref')}' does not resolve (domain:/facade:/service:/artifact:)"))
    return out


def _load_yaml(path):
    import yaml
    try:
        with open(path) as f:
            return yaml.safe_load(f)
    except Exception:  # noqa: BLE001
        return None


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
def _any_capability(m):
    return any(d.get("uses") or d.get("identity") or d.get("kind") in AGENT_KINDS for d in domains(m).values())
def _any_agent_endpoint(m):
    return any(is_agent(m, i.get("from")) or is_agent(m, i.get("to")) for i in interactions(m))
def _to_agent_or_auth(m):
    return any(is_agent(m, i.get("to")) or i.get("authorization") for i in interactions(m))

DISPATCH = [
    # (name, fn, predicate, [registries])
    ("check_topology",       check_topology,       lambda m: _has_typed_interactions(m) or m.get("orchestration") or segments(m), []),
    ("check_references",     check_references,     _has_typed_interactions, []),
    ("check_classification", check_classification, _compound_with_agent, []),
    ("check_scope_grammar",  check_scope_grammar,  _any_scope, []),
    ("check_capabilities",   check_capabilities,   _any_capability, ["capabilities"]),
    ("check_boundary_legs",  check_boundary_legs,  _any_agent_endpoint, []),
    ("check_authorization",  check_authorization,  _to_agent_or_auth, []),
    ("check_policy_refs",    check_policy_refs,    _has_policy_or_quant, ["policies"]),
    ("check_async",          check_async,          lambda m: any(i.get("kind") in ("async_task", "event") or i.get("async") for i in interactions(m)), []),
    ("check_memory",         check_memory,         lambda m: any(d.get("memory") for d in domains(m).values()), ["stores"]),
    ("check_lifecycle",      check_lifecycle,      lambda m: any(d.get("lifecycle") for d in domains(m).values()), ["stores"]),
    ("check_deep_agent",     check_deep_agent,     lambda m: any(d.get("kind") == "deep_agent" or d.get("deep_agent") for d in domains(m).values()), []),
    ("check_saga",           check_saga,           lambda m: bool(sagas(m)), ["policies"]),
    ("check_compensation_gap", check_compensation_gap, lambda m: bool(segments(m)), []),
    ("check_eval_coverage",  check_eval_coverage,  lambda m: any_agent(m) or bool(segments(m)), ["evals_index", "evals_waivers"]),
    ("check_observability",  check_observability,  any_agent, []),
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
