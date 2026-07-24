#!/usr/bin/env python3
"""Baseline eval-spec generator (CR-20 / LLD §7.4) for the compound-agentic surface.

Seeds a `kind: eval` spec for each mandatory target (every agent domain + each `e2e`
segment) that lacks one, with DETERMINISTIC case ids drawn from the target's
`owning_fr`, its facade `error_modes` (CR-6 failure modes), and its privilege
boundary. Merge-by-id PRESERVES human-edited cases (`edited: true`) on regeneration —
the generator seeds, humans own. Specs start `status: baseline` /
`approval.decision: baseline_only` so they do NOT satisfy Tier-2+ coverage until a
human approves (the eval gate, §6.12).

A deterministic component is NOT a mandatory target (opt in with a contract_test spec
by hand). This tool never approves a spec and never runs an eval.

  --write   (default) create/merge spec files on disk
  --check   report targets missing an approved-or-baseline spec; exit 2 if any missing
"""
from __future__ import annotations
import os
import sys

AGENT_KINDS = {"simple_agent", "deep_agent"}


def _domains(m):   return m.get("domains") or {}
def _segments(m):  return m.get("segments") or []


def _cases_for_component(name, d):
    cases = []
    fr = d.get("owning_fr")
    if fr:
        cases.append({"id": f"{name}_satisfies_{fr.lower().replace('-', '_')}",
                      "given": f"a representative input for {name}", "expect": f"behavior that satisfies {fr}",
                      "source": "acceptance_criterion", "edited": False})
    for api, spec in sorted((d.get("facade_apis") or {}).items()):
        for i, em in enumerate(spec.get("error_modes") or []):
            cases.append({"id": f"{name}_{api}_err{i}", "given": f"the failure condition: {em}",
                          "expect": "handled per the facade contract (no silent failure)",
                          "source": "failure_mode", "edited": False})
    if d.get("kind") in AGENT_KINDS and (d.get("uses") or d.get("identity")):
        cases.append({"id": f"{name}_privilege_boundary",
                      "given": "an attempt to act beyond the declared capabilities",
                      "expect": "the action is refused (least-privilege holds)",
                      "source": "boundary_check", "edited": False})
    if not cases:
        cases.append({"id": f"{name}_baseline", "given": "a representative input", "expect": "correct output",
                      "source": "acceptance_criterion", "edited": False})
    return cases


def _cases_for_segment(sid):
    return [{"id": f"{sid}_e2e", "given": "an end-to-end run of the segment",
             "expect": "the flow completes correctly and is traced", "source": "acceptance_criterion", "edited": False}]


def _merge(existing, seeded):
    """Preserve human-edited cases; refresh non-edited ones; add new seeds by id."""
    if not existing:
        return seeded
    by_id = {c["id"]: c for c in existing.get("cases", [])}
    out = []
    seen = set()
    for c in seeded:
        prior = by_id.get(c["id"])
        out.append(prior if (prior and prior.get("edited")) else c)
        seen.add(c["id"])
    for c in existing.get("cases", []):     # keep human-added edited cases not in the seed
        if c["id"] not in seen and c.get("edited"):
            out.append(c)
    merged = dict(existing)
    merged["cases"] = out
    return merged


def _spec(target_type, target_id, cases, existing):
    base = existing or {
        "target_type": target_type, "target_id": target_id, "kind": "eval",
        "owner": "TODO-assign-a-human-owner", "status": "baseline",
        "approval": {"reviewer": "", "date": "", "decision": "baseline_only"},
    }
    base = dict(base)
    base["cases"] = cases
    return base


def _targets(m):
    for name in sorted(_domains(m)):
        d = _domains(m)[name]
        if d.get("kind") in AGENT_KINDS:
            yield ("component", name, d, _cases_for_component(name, d))
    for s in _segments(m):
        if s.get("e2e"):
            yield ("segment", s.get("id"), s, _cases_for_segment(s.get("id")))


def generate(manifest_path, root, write=True):
    import yaml
    m = yaml.safe_load(open(manifest_path))
    missing, wrote = [], []
    for ttype, tid, node, cases in _targets(m):
        rel = f"docs/03-engineering/evals/{ttype}/{tid}.yaml"
        path = os.path.join(root, rel)
        existing = yaml.safe_load(open(path)) if os.path.exists(path) else None
        approved = bool(existing) and (existing.get("approval") or {}).get("decision") == "approved"
        if not existing:
            missing.append(rel)
        merged = _merge(existing, cases)
        spec = _spec(ttype, tid, merged["cases"] if isinstance(merged, dict) and "cases" in merged else cases, existing)
        if write:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as f:
                yaml.safe_dump(spec, f, sort_keys=False)
            wrote.append(rel)
    return missing, wrote


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="Baseline eval-spec generator (CR-20, #10)")
    ap.add_argument("manifest")
    ap.add_argument("--root", default=".")
    ap.add_argument("--check", action="store_true", help="report targets with no spec; exit 2 if any")
    a = ap.parse_args(argv)
    missing, wrote = generate(a.manifest, a.root, write=not a.check)
    if a.check:
        for r in missing:
            print(f"MISSING eval spec: {r}")
        print(f"{len(missing)} target(s) without a spec")
        return 2 if missing else 0
    print(f"seeded/merged {len(wrote)} eval spec(s); {len(missing)} were newly created")
    return 0


if __name__ == "__main__":
    sys.exit(main())
