#!/usr/bin/env python3
"""Phase-A (#13) verification: the compound-agentic schema extensions load, the
registry templates parse, the worked agentic example is schema-coherent and its
registry references resolve, and a legacy manifest is provably UNAFFECTED by the
extension (additive-only, ADR-13).

This runs before any validator exists (that is #16); it checks SHAPE + additivity,
not value-level pass/fail. Runnable directly (`python3 test_schema_and_examples.py`)
and as pytest (`test_*` functions).
"""
import os
import yaml

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _load(rel):
    with open(os.path.join(ROOT, rel)) as f:
        return yaml.safe_load(f)


SCHEMA = "ai/claude/generate-docs/templates/system-manifest.schema.yaml"
AGENTIC = "docs/examples/compound-agentic/system-manifest.yaml"
LEGACY = "docs/examples/greenfield/docs/system-manifest.yaml"
REGISTRIES = {
    "docs/03-engineering/approved-capabilities.yaml": ("capabilities", dict),
    "docs/03-engineering/policies.yaml": ("policies", dict),
    "docs/03-engineering/stores.yaml": ("stores", dict),
    "docs/03-engineering/evals/index.yaml": ("rows", list),
    "docs/03-engineering/evals/waivers.yaml": ("waivers", list),
}

NEW_TOP_LEVEL = ["interactions", "orchestration", "segments", "sagas", "observability"]
NEW_DOMAIN_FIELDS = ["kind", "kind_rationale", "owning_fr", "identity", "uses",
                     "memory", "lifecycle", "deep_agent", "evals"]


def test_installed_claude_schema_matches_source():
    """The packaged plugin's active schema (.claude/…) must equal the source schema
    (ai/claude/…) — else a built-plugin user gets a stale, non-compound schema
    (round-codex #2)."""
    src = os.path.join(ROOT, "ai/claude/generate-docs/templates/system-manifest.schema.yaml")
    installed = os.path.join(ROOT, ".claude/commands/skills/generate-docs/templates/system-manifest.schema.yaml")
    with open(src) as a, open(installed) as b:
        assert a.read() == b.read(), "installed .claude schema is out of sync with the source schema — resync it"


def test_schema_loads_and_declares_extensions():
    s = _load(SCHEMA)["schema"]
    for k in NEW_TOP_LEVEL:
        assert k in s, f"schema missing top-level `{k}`"
    de = s["domains"]["DomainEntry"]
    for k in NEW_DOMAIN_FIELDS:
        assert k in de, f"schema DomainEntry missing `{k}`"
    # nested structures present
    assert "InteractionElement" in s["interactions"]
    for nested in ("Leg", "AsyncSpec", "Authorization"):
        assert nested in s["interactions"]["InteractionElement"], f"missing {nested}"
    assert set(s["observability"]["Observability"]) == {"tracing", "cost_budget", "eval_console"}


def test_registries_parse():
    for rel, (key, typ) in REGISTRIES.items():
        d = _load(rel)
        assert d.get("schema_version") == "1.0", f"{rel}: schema_version"
        assert isinstance(d.get(key), typ), f"{rel}: `{key}` should be {typ.__name__}"


def test_agentic_example_is_schema_coherent():
    m = _load(AGENTIC)
    # uses the new blocks
    assert any(k in m for k in NEW_TOP_LEVEL), "agentic example uses no new top-level block"
    schema = _load(SCHEMA)["schema"]
    # every top-level key it uses is declared in the schema
    for k in m:
        assert k in schema, f"agentic example top-level `{k}` not in schema"
    # every domain agentic field is declared in DomainEntry
    de = schema["domains"]["DomainEntry"]
    known = set(de)
    for name, dom in m["domains"].items():
        for f in dom:
            assert f in known, f"domain {name}: field `{f}` not in DomainEntry schema"
    # at least one agent present, and the observability floor block is declared
    kinds = {d.get("kind") for d in m["domains"].values()}
    assert kinds & {"simple_agent", "deep_agent"}, "no agent in the agentic example"
    assert "observability" in m, "agentic example (has agents) must declare observability"


def test_agentic_example_registry_refs_resolve():
    m = _load(AGENTIC)
    caps = set(_load("docs/03-engineering/approved-capabilities.yaml")["capabilities"])
    pols = set(_load("docs/03-engineering/policies.yaml")["policies"])
    stores = set(_load("docs/03-engineering/stores.yaml")["stores"])

    for name, dom in m["domains"].items():
        for u in dom.get("uses", []):
            assert u["capability"] in caps, f"{name}: capability `{u['capability']}` not in registry"
        lt = (dom.get("memory") or {}).get("long_term")
        if lt:
            assert lt["store"] in stores, f"{name}: store `{lt['store']}` not in registry"

    for i in m.get("interactions", []):
        for leg in ("request", "response"):
            v = (i.get(leg) or {}).get("validation")
            if v:
                assert v in pols, f"interaction {i['id']}.{leg}: policy `{v}` not in registry"
    for sg in m.get("sagas", []):
        for st in sg["steps"]:
            assert st["compensation"] in pols, f"saga {sg['id']}: compensation `{st['compensation']}` not in registry"


def test_legacy_manifest_is_unaffected_additivity():
    """A legacy manifest uses NONE of the new blocks — proving the extension is
    additive (a deterministic manifest is untouched; per-check activation, ADR-13)."""
    m = _load(LEGACY)
    for k in NEW_TOP_LEVEL:
        assert k not in m, f"legacy fixture unexpectedly has top-level `{k}`"
    for name, dom in m["domains"].items():
        # legacy domains have no `kind` (⇒ deterministic) and no other agentic field
        for f in ("kind", "identity", "uses", "memory", "lifecycle", "deep_agent"):
            assert f not in dom, f"legacy domain {name} unexpectedly has `{f}`"


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for t in tests:
        t()
        print(f"  PASS  {t.__name__}")
        passed += 1
    print(f"\nPhase-A schema/example verification: {passed}/{len(tests)} passed")
