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
    ast.In, ast.NotIn, ast.USub, ast.UAdd,   # signed numeric literals (round-3 L3): `x == -1`
)


def validate(expr):
    """Return [] if `expr` is a valid §2.2 predicate, else a list of reasons."""
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as e:
        return [f"syntax error: {e}"]
    errs = []
    # a root name (answers/components/edges) is only meaningful as `<root>.<attr>`; used bare it is a
    # namespace object, not a boolean — reject it so it can't pass validate then TypeError at eval (round-4 F5)
    attr_bases = {id(n.value) for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    for node in ast.walk(tree):
        if isinstance(node, ALLOWED_NODES):
            continue
        if isinstance(node, ast.Name):
            if node.id in ATTR_ROOTS:
                if id(node) not in attr_bases:
                    errs.append(f"'{node.id}' must be used as {node.id}.<attr> (e.g. {node.id}.count)")
            elif node.id not in ALLOWED_NAMES:
                errs.append(f"name '{node.id}' is not in the grammar")
        elif isinstance(node, ast.Attribute):
            root = node.value
            if not (isinstance(root, ast.Name) and root.id in ATTR_ROOTS):
                errs.append("only answers.<factor> / components.count / edges.count are allowed")
            elif root.id in ("components", "edges") and node.attr != "count":
                errs.append(f"{root.id}.{node.attr}: only .count is allowed")
            elif root.id == "answers" and (node.attr.startswith("_") or not node.attr.isidentifier()):
                errs.append(f"answers.{node.attr}: not a valid factor name")
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
    try:
        return bool(eval(compile(ast.parse(expr, mode="eval"), "<ask_when>", "eval"), {"__builtins__": {}}, ns))
    except Exception as e:   # a grammar-valid predicate can still fail at runtime (e.g. -None) — one ValueError contract (round-4 F5)
        raise ValueError(f"ask_when '{expr}' failed to evaluate: {e}") from e
