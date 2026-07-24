#!/usr/bin/env python3
"""Agentic Design Advisor — records (EPIC #35 / LLD §7).

Reads/writes the canonical scenario state and GENERATES two durable artifacts from it:
  - the decision record `agentic-decisions.md` (a regenerate-and-diff Markdown view);
  - the NEUTRAL handoff `agentic-design-handoff.yaml` — recommendations + hints only,
    with NO `system-manifest.yaml` field, not even `kind` (round-9 B2). A human authors
    the real manifest from the handoff; #10 validates it.

The Advisor records a `skip` (an Advisor record, granting no #10 exception); the word
"waiver" is reserved for a human-authored #10 exception (ADV-12). Nothing here authors
a manifest field or runs a #10 validator — that boundary is the point of the feature.
"""
from __future__ import annotations
import os
import sys

try:
    import compose as _compose
except ImportError:  # when imported as a package
    from . import compose as _compose  # type: ignore

# Per-lens recommendation: the control the design should apply + WHERE (a manifest PATH
# hint, never a value). #10 validates the authored value (LLD §5.1 / §7.4).
LENS_RECS = {
    "classify":      ("proposed_kind + rationale per component (deep_agent structure where deep)",
                      "domains[<agent>].kind (+ deep_agent{...}) — authored anew by the design role"),
    "boundary":      ("inter-component contract + trust-leg controls (validate stochastic→deterministic; cost/authority into agents)",
                      "interactions[].response.validation + callee facade_apis"),
    "privilege":     ("least-privilege identity + per-use capabilities per agent",
                      "domains[<agent>].identity + .uses"),
    "reliability":   ("async idempotency/DLQ + lifecycle (human-gate/resumability) + kill-switch",
                      "interactions[].async + domains[<agent>].lifecycle + top-level sagas"),
    "observability": ("tracing + PM eval-console",
                      "top-level observability{tracing,eval_console} (#10 check_observability enforces)"),
    "memory":        ("memory/PII controls (durability, retrieval, PII handling)",
                      "domains[<agent>].memory.long_term"),
    "evals":         ("per-agent eval spec + one e2e flow",
                      "domains[<agent>].evals + segments[e2e].evals"),
    "deploy":        ("build-vs-buy decision (managed unless a reason to build) + portability diligence",
                      "carried to the platform/ops track (FR-25) — authors no manifest field"),
}
# The handoff's own NEUTRAL vocabulary (structural keys it legitimately shares with #10) — excluded
# from the guard so a component `id` / connection `from`/`to` / skip `owner` don't self-trip. This
# exclusion is sound ONLY because every emitted channel is scalar-coerced (`_text`/`_enum`), so a
# neutral key can appear only as the handoff's own scalar structural key — never as a smuggled dict
# key under a passthrough field. Do NOT emit any handoff field verbatim without coercion (round-4 F2).
_HANDOFF_NEUTRAL = {"id", "from", "to", "control", "owner", "reason"}
# A comprehensive static fallback (top-level + NESTED #10 field names) used if #10 isn't co-located.
_STATIC_MANIFEST_FIELDS = {
    "kind", "kind_rationale", "domains", "interactions", "facade_apis", "boundary_entities",
    "events_emitted", "events_consumed", "cross_cutting", "interaction_matrix", "uses", "identity",
    "memory", "lifecycle", "deep_agent", "orchestration", "segments", "sagas", "observability",
    "authorization", "async", "owning_fr", "evals", "depends_on", "conventions",
    # nested (round-2 F2): the full #10 vocabulary, not just wrappers
    "principal", "privilege", "capability", "operations", "resources", "short_term", "long_term",
    "strategy", "budget_tokens", "store", "durability", "retrieval", "scope", "shared_store", "pii",
    "pii_justification", "reads", "writes", "high_stakes", "provenance", "staleness", "high_stakes_guardrail",
    "long_running", "checkpoint", "checkpoint_store", "resume_cursor", "resumable", "idempotent_resume",
    "side_effect_key", "human_gate", "human_gate_pause", "timeout", "cancellation", "planner", "subagents",
    "context_isolation", "gates", "guardrails", "facade", "entity_crossing", "request", "response",
    "side_effecting", "validation", "cost_bound", "authority_bound", "delivery", "consumer_idempotent",
    "idempotency_key", "retry", "dlq", "dlq_justification", "replay", "allowed_callers", "audience",
    "credential_mode", "credential_justification", "pattern", "justification", "coordinator", "cycle_bound",
    "path", "e2e", "transactional", "compensation", "compensation_idempotent", "on_compensation_failure",
    "tracing", "cost_budget", "eval_console", "convention", "hops", "attributes", "access", "ref",
    "limit", "unit", "signature", "blurb", "mutations", "preconditions", "error_modes", "spec",
    # kept at parity with #10.FIELD_SPEC so the fallback is never weaker than the live derivation
    # (round-3 L1; a parity test in ci/agentic-advisor guards against future drift)
    "adr", "affected_domains", "backoff", "consumed_by", "date", "description", "enforcement", "files",
    "generated_at", "generator", "interaction_id", "last_changed", "lld", "max", "name", "note", "order",
    "purpose", "resource", "rule", "shape", "steps", "summary", "tests", "version",
}


def _manifest_field_names():
    """Every #10 manifest field name (top-level + NESTED), minus the neutral handoff identity keys.
    Derived from #10's authoritative FIELD_SPEC so it can't drift; static fallback if #10 is absent."""
    try:
        p = os.path.join(os.path.dirname(__file__), "..", "..", "ci", "manifest-agentic")
        if p not in sys.path:
            sys.path.insert(0, p)
        import check_manifest_agentic as _m10  # type: ignore
        names = set()
        for fields in _m10.FIELD_SPEC.values():
            names |= set(fields)
        return (names | _STATIC_MANIFEST_FIELDS) - _HANDOFF_NEUTRAL
    except Exception:  # noqa: BLE001
        return _STATIC_MANIFEST_FIELDS - _HANDOFF_NEUTRAL


MANIFEST_FIELDS = _manifest_field_names()
SKIP_FIELDS = ["control", "owner", "reason"]          # a skip is projected to exactly these (F2 channel)


def _text(v):
    """Coerce a free-text field to a scalar STRING so a dict/list can't smuggle nested manifest
    keys through an open channel (rationale/feature/skip) past the key-walking guard (F2)."""
    return "" if v is None else str(v)


def _enum(v):
    """Coerce an ELICITED-ENUM channel (role / proposed_kind / transport) to a scalar. These three
    are emitted for the human to eyeball, so a dict/list value would ride into the handoff verbatim
    and — keyed only on neutral names (id/from/to/owner) — smuggle a manifest value past the guard
    (round-4 F2). A non-scalar becomes None, which `validate_roles`/`validate_scenario` then flag on
    the underlying state. This is what makes the `_HANDOFF_NEUTRAL` exclusion sound."""
    return v if v is None or isinstance(v, (str, bool, int, float)) else None


def _sid(v):
    """A hashable scalar id, else None — so a container-valued id/attaches_to (unhashable) can't
    crash a set/dict build or an `in` test (round-4 F1). A malformed id degrades to unresolvable."""
    return v if isinstance(v, (str, int, float, bool)) else None


def build_recommendations(composed):
    """One recommendation per included lens; floor entries carry an advisory depth_note."""
    recs = []
    for lens in composed["report_sections"]:
        control, hint = LENS_RECS[lens]
        is_floor = lens in composed["floor"]
        # `category` (floor|rung), NOT `kind` — a bare `kind` key would be a manifest field (NO-AUTHOR)
        rec = {"id": f"r-{lens}-1", "lens": lens, "control": control,
               "target_path_hint": hint, "category": "floor" if is_floor else "rung"}
        if is_floor:
            rec["depth_note"] = "human-confirmed advisory depth (heavier at higher Tier/stakes; not a computed field)"
        recs.append(rec)
    return recs


def generate_handoff(state, composed=None):
    """The NEUTRAL `agentic-design-handoff.yaml` — elicited facts + recommendations/hints;
    NO manifest field (HANDOFF/NO-AUTHOR, §7.4)."""
    state = state or {}                                     # tolerate a None root (round-3 L4)
    composed = composed or _compose.compose(state)
    comps = [c for c in (state.get("components") or []) if isinstance(c, dict)]
    edges = [e for e in (state.get("edges") or []) if isinstance(e, dict)]
    skips = [sk for sk in (state.get("skips") or []) if isinstance(sk, dict)]
    return {
        "schema_version": "1.0",
        "feature": _text(state.get("feature", "<feature>")),
        # elicited neutral facts (role/transport) + a proposed_kind RECOMMENDATION (never a `kind:` field).
        # EVERY channel is scalar-coerced at emit: free-text via _text, elicited enums via _enum — so no
        # channel (not even the verbatim-looking ones) can carry a nested manifest fragment (F2, round-4 F2).
        "components": [{"id": _text(c.get("id")), "role": _enum(c.get("role")), "proposed_kind": _enum(c.get("proposed_kind")),
                        "rationale": _text(c.get("rationale", ""))} for c in comps],
        "connections": [{"from": _text(e.get("from")), "to": _text(e.get("to")), "transport": _enum(e.get("transport"))} for e in edges],
        "recommendations": build_recommendations(composed),
        # skips are PROJECTED to {control,owner,reason} and STRINGIFIED — not passed verbatim (closes the F2 channel)
        "skips": [{k: _text(sk.get(k)) for k in SKIP_FIELDS} for sk in skips],
    }


def validate_skips(state):
    """FLOOR-SKIP-SILENT (F8): a recorded skip must name control + owner + reason as non-empty
    SCALARS — never silent, never a smuggled structure. Must not crash on malformed input."""
    state = state or {}                                     # tolerate a None root (round-4 F4)
    errs = []
    for sk in (state.get("skips") or []):
        if not isinstance(sk, dict):
            errs.append(f"skip must be a mapping: {sk!r}")
            continue
        for k in SKIP_FIELDS:
            v = sk.get(k)
            if isinstance(v, (dict, list)) or not str(v if v is not None else "").strip():
                errs.append(f"skip {sk.get('control', '?')}: field '{k}' must be a non-empty scalar")
    return errs


def validate_decision_refs(state):
    """Finalize-time check (round-3 M2): every decision's `attaches_to` resolves to a real
    component/edge/lens id and every `depends_on` path has a known root. A typo here silently
    disables staleness/retirement on rerun, so surface it before handoff. Returns warnings."""
    state = state or {}
    comp = {_sid(c.get("id")) for c in (state.get("components") or []) if isinstance(c, dict)} - {None}
    edge = {_sid(e.get("id")) for e in (state.get("edges") or []) if isinstance(e, dict)} - {None}
    targets = comp | edge | set(_compose.LENSES)
    warns = []
    for d in (state.get("decisions") or []):
        if not isinstance(d, dict):
            continue
        att = d.get("attaches_to")
        if att is not None and _sid(att) not in targets:   # _sid guards an unhashable att (round-4 F1)
            warns.append(f"decision {d.get('id', '?')}: attaches_to '{att}' resolves to no component/edge/lens")
        dep = d.get("depends_on")
        if dep is not None and not isinstance(dep, (str, list)):   # a dict/other depends_on can't resolve (round-4 F6)
            warns.append(f"decision {d.get('id', '?')}: depends_on {dep!r} is malformed (expected a path string or list)")
        for path in ([dep] if isinstance(dep, str) else (dep if isinstance(dep, list) else [])):
            if _resolve(state, path) is None:   # at finalize every gating input should resolve; None ⇒ typo/gap
                warns.append(f"decision {d.get('id', '?')}: depends_on '{path}' resolves to nothing (typo or uncaptured input)")
    return warns


def handoff_ref_integrity(handoff):
    """HANDOFF-REF-INTEGRITY (§7.4/§9): recommendation ids are unique and every
    target_path_hint is a non-empty PATH string (a WHERE, never an authored value)."""
    errs = []
    seen = set()
    for r in handoff.get("recommendations", []):
        rid = r.get("id")
        if rid in seen:
            errs.append(f"duplicate recommendation id '{rid}'")
        seen.add(rid)
        hint = r.get("target_path_hint")
        if not isinstance(hint, str) or not hint.strip():
            errs.append(f"recommendation '{rid}': target_path_hint must be a non-empty path string")
    return errs


def handoff_authors_no_manifest_field(handoff):
    """NO-AUTHOR (§9): the handoff contains no `system-manifest.yaml` field value (no `kind`,
    no `interactions`, …). Returns the set of offending keys found anywhere (empty ⇒ clean)."""
    found = set()
    def walk(x):
        if isinstance(x, dict):
            for k, v in x.items():
                if k in MANIFEST_FIELDS:
                    found.add(k)
                walk(v)
        elif isinstance(x, list):
            for e in x:
                walk(e)
    walk(handoff)
    return found


def generate_decision_record(state, composed=None):
    """`agentic-decisions.md` — a pure function of the state (REC-GEN, regenerate-and-diff)."""
    state = state or {}                                     # tolerate a None root (round-3 L4)
    composed = composed or _compose.compose(state)
    not_needed = [l for l in _compose.LENSES if l not in composed["report_sections"]]
    lines = [f"# Agentic design decisions — {state.get('feature', '<feature>')}", "",
             "*Generated from `.hitl/agentic-state.yaml` — do not edit (regenerate-and-diff).*", "",
             "## Recommended workflow", "",
             f"- **Floor (shouldn't be skipped):** {', '.join(composed['floor']) or '(none)'}",
             f"- **Offered rungs:** {', '.join(composed['rungs']) or '(none)'}",
             f"- **Not needed:** {', '.join(not_needed) or '(none)'}", "",
             "## Recommendations (a human authors the manifest; #10 validates)", ""]
    for r in build_recommendations(composed):
        lines.append(f"- **{r['lens']}** ({r['category']}) — {r['control']}  ·  hint: `{r['target_path_hint']}`")
    decs = [d for d in (state.get("decisions") or []) if isinstance(d, dict)]   # tolerate junk entries (round-3 H2)
    if decs:
        lines += ["", "## Menu decisions (chosen / rejected / rationale)", ""]
        for d in decs:
            rejected = d.get("rejected")
            rej = ", ".join(str(x) for x in rejected) if isinstance(rejected, list) else "—"
            state_tag = f" [{d['state']}]" if d.get("state") else ""
            lines.append(f"- **{d.get('attaches_to', '?')}**{state_tag}: chose **{d.get('chosen')}** "
                         f"(rejected: {rej}) — {d.get('rationale', '')}"
                         + ("  · OVERRIDE" if d.get("override") else ""))
    skps = [s for s in (state.get("skips") or []) if isinstance(s, dict)]
    if skps:
        lines += ["", "## Recorded skips (Advisor records — grant no #10 gate exception)", ""]
        for s in skps:
            lines.append(f"- `{s.get('control')}` — owner {s.get('owner')}, reason: {s.get('reason')}")
    if state.get("deploy"):
        d = state["deploy"]
        lines += ["", "## Deploy decision (recorded, human-carried)", "",
                  f"- recommend **{d.get('recommend')}**, chosen **{d.get('chosen')}** — carried to {d.get('carry_to', 'platform/ops (FR-25)')}"]
    return "\n".join(lines) + "\n"


def _resolve(state, path):
    """Resolve a dotted state path like 'answers.side_effects' (for a decision's depends_on)."""
    cur = state
    for part in str(path).split("."):
        if isinstance(cur, dict):
            cur = cur.get(part)
        else:
            return None
    return cur


def reconcile(old_state, new_scenario):
    """Re-run = recompute derived + reconcile human-owned decisions by id (§7.3). A decision is
    flagged `stale` if a gating input changed — the attached component's proposed_kind OR any
    `depends_on` state field (e.g. `answers.side_effects` moving to irreversible). A decision on
    a removed component OR edge is `retired`. skips AND deferrals AND deploy are carried, never
    silently dropped. Returns a diff-ready state (the human confirms before write)."""
    old_state, new_scenario = old_state or {}, new_scenario or {}   # tolerate a None root (round-3 L4)
    new = dict(new_scenario)
    def _by_id(state, key):     # id-keyed, tolerating id-less / non-dict / unhashable-id entries (F4, round-4 F1)
        out = {}
        for x in (state.get(key) or []):
            if isinstance(x, dict) and _sid(x.get("id")) is not None:
                out[x["id"]] = x
        return out
    old_comp, old_edge = _by_id(old_state, "components"), _by_id(old_state, "edges")
    new_comp, new_edge = _by_id(new_scenario, "components"), _by_id(new_scenario, "edges")
    targets = set(new_comp) | set(new_edge) | set(_compose.LENSES)  # where a live attaches_to may point
    decisions, retired, warnings = [], [], []
    for d in (old_state.get("decisions") or []):
        if not isinstance(d, dict):
            continue
        att = _sid(d.get("attaches_to"))   # unhashable att degrades to None (unresolvable) rather than crashing (round-4 F1)
        # A decision attaches to a SPECIFIC entity. Retire it when the id is gone from every namespace
        # it lived in — but a same-id flip (component x removed while edge x appears) is NOT the same
        # entity, so it must retire too, not silently survive on the impostor (round-3 M1 + round-4 F3).
        old_ns = [ns for ns, m in (("comp", old_comp), ("edge", old_edge)) if att in m]
        still_live = any((ns == "comp" and att in new_comp) or (ns == "edge" and att in new_edge) for ns in old_ns)
        if old_ns and not still_live:
            retired.append({**d, "state": "retired"})
            continue
        if att is not None and att not in targets:                 # a ghost id can't go stale/retired — surface it (round-3 M2)
            warnings.append(f"decision {d.get('id', '?')}: attaches_to '{att}' resolves to no component/edge/lens (typo? re-review disabled)")
        stale = False
        if att in new_comp and old_comp.get(att, {}).get("proposed_kind") != new_comp[att].get("proposed_kind"):
            stale = True
        dep = d.get("depends_on")
        if dep is not None and not isinstance(dep, (str, list)):    # a dict/other depends_on can't resolve (round-4 F6)
            warnings.append(f"decision {d.get('id', '?')}: depends_on {dep!r} is malformed (expected a path string or list)")
        for path in ([dep] if isinstance(dep, str) else (dep if isinstance(dep, list) else [])):  # a string is ONE path (F4)
            ov, nv = _resolve(old_state, path), _resolve(new_scenario, path)
            if ov is None and nv is None:   # a typo'd / uncaptured path resolves None on both sides ⇒ never stale (round-3 M2)
                warnings.append(f"decision {d.get('id', '?')}: depends_on '{path}' resolves to nothing in either state (typo or uncaptured input? staleness can't fire)")
            if ov != nv:
                stale = True
        decisions.append({**d, "state": "stale" if stale else "confirmed"})
    new["decisions"] = decisions
    new["retired"] = retired
    new["warnings"] = warnings                              # human sees typo'd refs before confirming the diff
    new["skips"] = old_state.get("skips", [])
    new["deferrals"] = old_state.get("deferrals", [])       # carried, never silently dropped (F4)
    if "deploy" in old_state:
        new["deploy"] = old_state["deploy"]
    return new
