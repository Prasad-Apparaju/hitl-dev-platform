#!/usr/bin/env python3
"""Agentic Design Advisor — the evolving system map (EPIC #35 / LLD §6, ADR-A8).

`render(scenario, composed) -> {terminal, mermaid}` — two CORE renderings from one
data source (round-4 M8). Terminal-first (no browser); Markdown/Mermaid for IDE/GitHub.
The rich HTML rendering + combined "chat + live map" mode are a DEFERRED enhancement (#43).

Every node's visual keys off its `role` — a single, directly-elicited, REQUIRED enum
(ROLE-TOTAL, §6.1): {agent, service, datastore, external, store}. The renderer reads the
scenario only (no manifest — there is none). Deterministic (regenerate-and-diff).
"""
from __future__ import annotations

try:
    import compose as _compose
except ImportError:
    from . import compose as _compose  # type: ignore

ROLES = {"agent", "service", "datastore", "external", "store"}
# (mermaid open/close, terminal ASCII prefix) per role
ROLE_STYLE = {
    "agent":     ("{{", "}}", "⬡"),
    "service":   ("[", "]", "▢"),
    "datastore": ("[(", ")]", "⛁"),
    "external":  ("([", "])", "☁"),
    "store":     ("[[", "]]", "▤"),
}
# Valid Mermaid link forms only: solid `-->` and dotted `-.->`; the transport goes in the
# (always non-empty) pipe label — an inline `-. x .->` combined with a pipe label is a parse
# error (round-fable-advisor F6).
EDGE = {"sync_call": "-->", "async_task": "-.->", "event": "-.->"}


# Accessors mirror compose (advisor-F3): a MISSING or present-but-None section (`components:\n`
# in a mid-intake YAML) degrades to empty and a non-dict entry is skipped — the map never crashes.
def _comps(s):   return [c for c in _compose._list(s, "components") if isinstance(c, dict)]
def _edges(s):   return [e for e in _compose._list(s, "edges") if isinstance(e, dict)]


def validate_roles(scenario):
    """ROLE-TOTAL: every component has exactly one role from the enum. Returns offending ids."""
    bad = []
    for c in _comps(scenario):
        role = c.get("role")
        # a container-valued role is unhashable — guard the `in` so the gate flags it, not crashes (round-4 F1)
        if not isinstance(role, str) or role not in ROLES:
            bad.append(c.get("id"))
    return bad


def _breakdown(scenario, composed):
    included = set(composed["report_sections"])
    getting = sorted(composed["floor"])                 # floor = recommended-mandatory
    available = sorted(composed["rungs"])               # offered, deferrable
    not_needed = [l for l in _compose.LENSES if l not in included]
    return getting, available, not_needed


def render_terminal(scenario, composed):
    lines = [f"{scenario.get('feature', 'agentic system')} · compound-agentic surface"]
    for c in _comps(scenario):
        _, _, icon = ROLE_STYLE.get(c.get("role"), ("", "", "?"))
        pk = c.get("proposed_kind")
        lines.append(f"  {icon} {c.get('id')}  ({c.get('role')}{' · ' + pk if pk else ''})")
    for e in _edges(scenario):
        arrow = {"sync_call": "─▶", "async_task": "··▶", "event": "··✉··▶"}.get(e.get("transport"), "─▶")
        lines.append(f"    {e.get('from')} {arrow} {e.get('to')}")
    getting, available, not_needed = _breakdown(scenario, composed)
    lines += [f"  getting:    {' · '.join(getting) or '(none)'}",
              f"  available:  {' · '.join(available) or '(none)'}",
              f"  not needed: {' · '.join(not_needed) or '(none)'}"]
    return "\n".join(lines) + "\n"


def render_mermaid(scenario, composed):
    lines = ["```mermaid", "graph LR"]
    for c in _comps(scenario):
        lo, hi, _ = ROLE_STYLE.get(c.get("role"), ("[", "]", ""))
        cid = c.get("id")
        lines.append(f"  {cid}{lo}{cid} · {c.get('role')}{hi}")
    for e in _edges(scenario):
        arrow = EDGE.get(e.get("transport"), "-->")
        label = e.get("id") or e.get("transport") or "edge"     # never empty (|| is a parse error)
        lines.append(f"  {e.get('from')} {arrow}|{label}| {e.get('to')}")
    lines.append("```")
    return "\n".join(lines) + "\n"


def render(scenario, composed=None):
    scenario = scenario or {}                               # tolerate a None root (round-3 L4)
    composed = composed or _compose.compose(scenario)
    return {"terminal": render_terminal(scenario, composed),
            "mermaid": render_mermaid(scenario, composed)}
