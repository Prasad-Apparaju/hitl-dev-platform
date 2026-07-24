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
MANIFEST_FIELDS = {"kind", "domains", "interactions", "facade_apis", "uses", "identity", "sagas"}  # NO-AUTHOR guard


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
    composed = composed or _compose.compose(state)
    return {
        "schema_version": "1.0",
        "feature": state.get("feature", "<feature>"),
        # elicited neutral facts (role/transport) + a proposed_kind RECOMMENDATION (never a `kind:` field)
        "components": [{"id": c["id"], "role": c["role"], "proposed_kind": c.get("proposed_kind"),
                        "rationale": c.get("rationale", "")} for c in state["components"]],
        "connections": [{"from": e["from"], "to": e["to"], "transport": e.get("transport")} for e in state["edges"]],
        "recommendations": build_recommendations(composed),
        "skips": state.get("skips", []),        # a recorded skip {control,owner,reason} — NOT a #10 waiver
    }


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
    if state.get("skips"):
        lines += ["", "## Recorded skips (Advisor records — grant no #10 gate exception)", ""]
        for s in state["skips"]:
            lines.append(f"- `{s.get('control')}` — owner {s.get('owner')}, reason: {s.get('reason')}")
    if state.get("deploy"):
        d = state["deploy"]
        lines += ["", "## Deploy decision (recorded, human-carried)", "",
                  f"- recommend **{d.get('recommend')}**, chosen **{d.get('chosen')}** — carried to {d.get('carry_to', 'platform/ops (FR-25)')}"]
    return "\n".join(lines) + "\n"


def reconcile(old_state, new_scenario):
    """Re-run = recompute derived + reconcile human-owned decisions by id (§7.3). A decision
    whose gating input (proposed_kind / a risk answer) changed is flagged `stale` for
    re-confirmation; a removed component's decisions are `retired`; unchanged are kept.
    Returns the reconciled state as a diff-ready dict (the human confirms before write)."""
    new = dict(new_scenario)
    old_comp = {c["id"]: c for c in old_state.get("components", [])}
    new_ids = {c["id"] for c in new_scenario.get("components", [])}
    decisions, retired = [], []
    for d in old_state.get("decisions", []):
        att = d.get("attaches_to")
        if att in old_comp and att not in new_ids:
            retired.append({**d, "state": "retired"})
            continue
        prev = old_comp.get(att, {})
        cur = next((c for c in new_scenario.get("components", []) if c["id"] == att), {})
        changed = prev.get("proposed_kind") != cur.get("proposed_kind")
        decisions.append({**d, "state": "stale" if changed else "confirmed"})
    new["decisions"] = decisions
    new["retired"] = retired
    new["skips"] = old_state.get("skips", [])        # skips are reconciled, never silently dropped
    return new
