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
# NO-AUTHOR guard — the FULL #10 manifest vocabulary (F2). A handoff key that is a manifest
# field name is a boundary violation. (proposed_kind / role / transport / target_path_hint are
# NOT manifest fields — they are the Advisor's recommendation/neutral vocabulary and stay allowed.)
MANIFEST_FIELDS = {
    "kind", "kind_rationale", "domains", "interactions", "facade_apis", "boundary_entities",
    "events_emitted", "events_consumed", "cross_cutting", "interaction_matrix", "uses", "identity",
    "memory", "lifecycle", "deep_agent", "orchestration", "segments", "sagas", "observability",
    "authorization", "async", "owning_fr", "evals",
}
SKIP_FIELDS = {"control", "owner", "reason"}          # a skip is projected to exactly these (F2 channel)


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
        # skips are PROJECTED to {control,owner,reason} — not passed verbatim (closes the F2 channel)
        "skips": [{k: sk.get(k) for k in SKIP_FIELDS} for sk in state.get("skips", [])],
    }


def validate_skips(state):
    """FLOOR-SKIP-SILENT (F8): a recorded skip must name control + owner + reason — never silent."""
    errs = []
    for sk in state.get("skips", []):
        missing = [k for k in SKIP_FIELDS if not (sk.get(k) or "").strip()]
        if missing:
            errs.append(f"skip {sk.get('control', '?')}: missing {missing} (a skip must record control+owner+reason)")
    return errs


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
    if state.get("decisions"):
        lines += ["", "## Menu decisions (chosen / rejected / rationale)", ""]
        for d in state["decisions"]:
            rej = ", ".join(str(x) for x in (d.get("rejected") or [])) or "—"
            state_tag = f" [{d['state']}]" if d.get("state") else ""
            lines.append(f"- **{d.get('attaches_to', '?')}**{state_tag}: chose **{d.get('chosen')}** "
                         f"(rejected: {rej}) — {d.get('rationale', '')}"
                         + ("  · OVERRIDE" if d.get("override") else ""))
    if state.get("skips"):
        lines += ["", "## Recorded skips (Advisor records — grant no #10 gate exception)", ""]
        for s in state["skips"]:
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
    new = dict(new_scenario)
    old_comp = {c["id"]: c for c in old_state.get("components", [])}
    old_edge = {e["id"]: e for e in old_state.get("edges", [])}
    new_comp = {c["id"]: c for c in new_scenario.get("components", [])}
    new_edge_ids = {e["id"] for e in new_scenario.get("edges", [])}
    decisions, retired = [], []
    for d in old_state.get("decisions", []):
        att = d.get("attaches_to")
        removed = (att in old_comp and att not in new_comp) or (att in old_edge and att not in new_edge_ids)
        if removed:
            retired.append({**d, "state": "retired"})
            continue
        stale = False
        if att in new_comp and old_comp.get(att, {}).get("proposed_kind") != new_comp[att].get("proposed_kind"):
            stale = True
        for path in d.get("depends_on", []):        # a changed risk answer / state field ⇒ stale
            if _resolve(old_state, path) != _resolve(new_scenario, path):
                stale = True
        decisions.append({**d, "state": "stale" if stale else "confirmed"})
    new["decisions"] = decisions
    new["retired"] = retired
    new["skips"] = old_state.get("skips", [])
    new["deferrals"] = old_state.get("deferrals", [])       # carried, never silently dropped (F4)
    if "deploy" in old_state:
        new["deploy"] = old_state["deploy"]
    return new
