#!/usr/bin/env python3
"""Agentic Design Advisor — the `ask_when` safe evaluator (EPIC #35 / LLD §2.2).

A SMALL SAFE evaluator (no arbitrary code): an `ask_when` predicate is a boolean expression
over exactly the §2.2 grammar — `components.count`, `edges.count`, `answers.<factor>`,
`any_agent`, `any_async`, the booleans `true`/`false`, and the operators
`>= <= == != and or not in`. Anything else (calls, lambdas, subscripts, attribute walks,
dunders) is rejected at validate() time, so the classic `().__class__...` escape can't parse.
"""
from __future__ import annotations
import ast
import types

ALLOWED_NAMES = {"any_agent", "any_async", "true", "false"}
ATTR_ROOTS = {"answers", "components", "edges"}
ALLOWED_NODES = (
    ast.Expression, ast.BoolOp, ast.And, ast.Or, ast.UnaryOp, ast.Not, ast.Compare, ast.Load,
    ast.Constant, ast.List, ast.Tuple, ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
    ast.In, ast.NotIn,
)


def validate(expr):
    """Return [] if `expr` is a valid §2.2 predicate, else a list of reasons."""
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as e:
        return [f"syntax error: {e}"]
    errs = []
    for node in ast.walk(tree):
        if isinstance(node, ALLOWED_NODES):
            continue
        if isinstance(node, ast.Name):
            if node.id not in ALLOWED_NAMES and node.id not in ATTR_ROOTS:
                errs.append(f"name '{node.id}' is not in the grammar")
        elif isinstance(node, ast.Attribute):
            if not (isinstance(node.value, ast.Name) and node.value.id in ATTR_ROOTS):
                errs.append("only answers.<factor> / components.count / edges.count are allowed")
        else:
            errs.append(f"disallowed expression: {type(node).__name__}")
    return errs


class _Answers:
    """Attribute access over the answers dict; a missing factor is None (not asked yet)."""
    def __init__(self, d): self._d = d or {}
    def __getattr__(self, k): return self._d.get(k)


def evaluate(expr, scenario):
    """Evaluate a validated predicate against a scenario. Raises ValueError if `expr` is
    outside the grammar. `scenario` supplies components/edges (lists) and answers (dict);
    any_agent/any_async are computed here so callers need not precompute them."""
    errs = validate(expr)
    if errs:
        raise ValueError("; ".join(errs))
    comps = scenario.get("components", [])
    ns = {
        "any_agent": any(c.get("proposed_kind") in ("simple_agent", "deep_agent") for c in comps),
        "any_async": any(e.get("transport") in ("async_task", "event") for e in scenario.get("edges", [])),
        "true": True, "false": False,
        "answers": _Answers(scenario.get("answers", {})),
        "components": types.SimpleNamespace(count=len(comps)),
        "edges": types.SimpleNamespace(count=len(scenario.get("edges", []))),
    }
    return bool(eval(compile(ast.parse(expr, mode="eval"), "<ask_when>", "eval"), {"__builtins__": {}}, ns))
