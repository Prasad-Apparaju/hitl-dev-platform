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


def validate_roles(scenario):
    """ROLE-TOTAL: every component has exactly one role from the enum. Returns offending ids."""
    bad = []
    for c in scenario["components"]:
        if c.get("role") not in ROLES:
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
    for c in scenario["components"]:
        _, _, icon = ROLE_STYLE.get(c.get("role"), ("", "", "?"))
        lines.append(f"  {icon} {c['id']}  ({c.get('role')}{' · ' + c['proposed_kind'] if c.get('proposed_kind') else ''})")
    for e in scenario["edges"]:
        arrow = {"sync_call": "─▶", "async_task": "··▶", "event": "··✉··▶"}.get(e.get("transport"), "─▶")
        lines.append(f"    {e['from']} {arrow} {e['to']}")
    getting, available, not_needed = _breakdown(scenario, composed)
    lines += [f"  getting:    {' · '.join(getting) or '(none)'}",
              f"  available:  {' · '.join(available) or '(none)'}",
              f"  not needed: {' · '.join(not_needed) or '(none)'}"]
    return "\n".join(lines) + "\n"


def render_mermaid(scenario, composed):
    lines = ["```mermaid", "graph LR"]
    for c in scenario["components"]:
        lo, hi, _ = ROLE_STYLE.get(c.get("role"), ("[", "]", ""))
        label = f"{c['id']} · {c.get('role')}"
        lines.append(f"  {c['id']}{lo}{label}{hi}")
    for e in scenario["edges"]:
        arrow = EDGE.get(e.get("transport"), "-->")
        label = e.get("id") or e.get("transport") or "edge"     # never empty (|| is a parse error)
        lines.append(f"  {e['from']} {arrow}|{label}| {e['to']}")
    lines.append("```")
    return "\n".join(lines) + "\n"


def render(scenario, composed=None):
    composed = composed or _compose.compose(scenario)
    return {"terminal": render_terminal(scenario, composed),
            "mermaid": render_mermaid(scenario, composed)}
