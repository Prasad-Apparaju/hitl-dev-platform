#!/usr/bin/env python3
"""Catalog lint for the Advisor (#36 / LLD §2.1-§2.3, test-plan CAT-*).

Proves the curated expertise data is well-formed: every ADV-2 lens is covered, every
question maps to a resolvable consequence (no orphan questions, ADV-4), every ask_when
predicate parses, and NO consequence targets a #10 manifest field (the Advisor authors
nothing #10 validates)."""
import os
import sys
import yaml

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "tools", "agentic-advisor"))
import compose as C

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CATALOG = os.path.join(ROOT, "ai/shared/agentic/catalog.yaml")

# ADV-2 lenses (§2.1) — every one must have ≥1 catalog entry.
CATALOG_LENSES = {"right-sizing", "determinism-boundary", "irreversibility", "human-gate", "privilege",
                  "topology", "reliability", "observability", "kill-switch", "memory", "pii",
                  "portability", "evaluation", "cost", "deployment", "stakes-tier"}
REPORT_SECTIONS = set(C.LENSES)
KINDS = {"classify", "boundary", "gate", "lens", "floor", "recommendation", "recorded_artifact"}
ROLES = {"pm", "technical_advisor", "architect", "developer", "qa", "ops"}


def _catalog():
    with open(CATALOG) as f:
        return yaml.safe_load(f)


def test_catalog_loads_and_covers_every_lens():
    cat = _catalog()
    assert cat.get("schema_version") and cat.get("owner") in ROLES and cat.get("refresh_cadence")
    covered = {e["lens"] for e in cat["entries"]}
    assert CATALOG_LENSES <= covered, f"CAT-COVERAGE: lenses with no entry: {sorted(CATALOG_LENSES - covered)}"


def test_consequence_schema_and_no_manifest_target():
    for e in _catalog()["entries"]:
        cons = e.get("consequence")
        assert isinstance(cons, dict) and cons != {}, f"{e['id']}: consequence must be a non-empty map"
        # every declared option (or a "*" default) has a consequence key
        opts = e.get("options") or ["*"]
        if opts != ["*"]:
            for o in opts:
                assert o in cons or "*" in cons, f"{e['id']}: option '{o}' has no consequence key"
        for key, items in cons.items():
            assert isinstance(items, list), f"{e['id']}.{key}: consequence must be a list"
            for it in items:
                assert it.get("kind") in KINDS, f"{e['id']}.{key}: bad kind {it.get('kind')}"
                assert "manifest_field" != it.get("kind"), "no manifest_field kind (Advisor authors no #10 field)"
                tgt = it.get("target")
                if it["kind"] in ("recommendation", "recorded_artifact"):
                    assert tgt.startswith("r-") and tgt.rsplit("-", 1)[0][2:] in REPORT_SECTIONS, f"{e['id']}: rec target '{tgt}'"
                else:
                    assert tgt in REPORT_SECTIONS, f"{e['id']}.{key}: lens/floor target '{tgt}' not a report section"


def test_roles_are_real():
    for e in _catalog()["entries"]:
        assert e.get("role") in ROLES, f"{e['id']}: role '{e.get('role')}'"


def test_ask_when_predicates_parse_and_evaluate():
    """CAT-ASK-WHEN: each ask_when is a safe boolean expr over the §2.2 grammar and
    evaluates without error against a sample scenario."""
    import types
    class _Count:
        def __init__(self, n): self.count = n
    ns = {"__builtins__": {}, "any_agent": True, "any_async": False,
          "true": True, "false": False,      # §2.2 grammar booleans (lowercase)
          "components": _Count(2), "edges": _Count(1),
          "answers": types.SimpleNamespace(side_effects="irreversible", autonomy="supervised", data="pii",
                                           greenfield=True, changes_platform=False, adds_durable_runtime=False,
                                           deploy_requested=False)}
    for e in _catalog()["entries"]:
        expr = e["ask_when"]
        try:
            eval(compile(expr, "<ask_when>", "eval"), dict(ns))  # noqa: S307 — trusted curated data, empty builtins
        except Exception as ex:  # noqa: BLE001
            raise AssertionError(f"{e['id']}: ask_when '{expr}' failed to evaluate: {ex}")


def test_entry_ids_unique():
    ids = [e["id"] for e in _catalog()["entries"]]
    assert len(ids) == len(set(ids))


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"  PASS  {t.__name__}")
    print(f"\nCatalog lint (#36/wave B): {len(tests)}/{len(tests)} passed")
