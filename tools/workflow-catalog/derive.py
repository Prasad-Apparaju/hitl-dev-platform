#!/usr/bin/env python3
"""Derive numbered workflow views from the numberless catalog.

The numberless catalog (`catalog.yaml`) is the Phase-1 source of truth: stable
`key`s, first-class `phases`, no stored `n`/`total`. This generator derives the
positional numbers (`n`, `total`, `phase.step`) that the runtime `workflows.yaml`
and the breadcrumb need, so numbers live only at the display layer.

The linchpin is `verify`: it derives every workflow and checks the result matches
the current runtime `ai/shared/workflows.yaml` (on n/key/label/phase/total). A
clean verify proves the eventual cutover (Phase 2) is lossless.

Usage:
  python3 tools/workflow-catalog/derive.py verify [--catalog ...] [--runtime ...]
  python3 tools/workflow-catalog/derive.py overview            # markdown overview to stdout
  python3 tools/workflow-catalog/derive.py numbered <name>     # derived numbered steps

Dependencies: Python 3.10+, PyYAML.
"""

from __future__ import annotations

import argparse
import string
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
DEFAULT_CATALOG = HERE / "catalog.yaml"
DEFAULT_RUNTIME = HERE.parent.parent / "ai" / "shared" / "workflows.yaml"

# Map a numberless catalog entry to its runtime workflow id.
#   spine            -> development (Feature profile = spine with no conditional steps)
#   workflows.<name> -> <name>, except greenfield -> prd
RUNTIME_ID = {"spine": "development", "greenfield": "prd"}


def runtime_id(catalog_name: str) -> str:
    return RUNTIME_ID.get(catalog_name, catalog_name)


# ---------------------------------------------------------------------------
# Derivation
# ---------------------------------------------------------------------------

def derive_steps(steps: list[dict]) -> list[dict]:
    """Assign derived n / phase.step to an ordered step list.

    A normal step increments the integer counter. A substep keeps the parent's
    integer and appends a letter (a, b, ...). Substeps never increment `total`.
    """
    out: list[dict] = []
    n = 0
    sub_letter = 0
    phase_counts: dict[str, int] = {}
    phase_sub: dict[str, int] = {}
    for s in steps:
        phase = s.get("phase", "")
        if s.get("substep"):
            sub_letter += 1
            letter = string.ascii_lowercase[sub_letter - 1]
            num = f"{n}{letter}"
            phase_sub[phase] = phase_sub.get(phase, 0) + 1
            pstep = f"{phase}.{phase_counts.get(phase, 0)}{letter}"
        else:
            n += 1
            sub_letter = 0
            num = str(n)
            phase_counts[phase] = phase_counts.get(phase, 0) + 1
            pstep = f"{phase}.{phase_counts[phase]}"
        out.append({
            "n": num,
            "key": s["key"],
            "label": s.get("label", ""),
            "phase": phase,
            "phase_step": pstep,
        })
    return out


def total_of(derived: list[dict]) -> int:
    return max((int(d["n"]) for d in derived if d["n"].isdigit()), default=0)


def active_steps(steps: list[dict], active: set[str] | None) -> list[dict]:
    """Drop conditional steps whose activator is not in `active`.

    A step with no `cond` is always included. `cond: <name>` is included only
    when <name> is in the active set. None means base (no conditions active).
    """
    active = active or set()
    return [s for s in steps if "cond" not in s or s["cond"] in active]


def workflow_steps(catalog: dict, name: str, active: set[str] | None = None) -> list[dict]:
    if name == "spine":
        return active_steps(catalog["spine"]["steps"], active)
    return catalog["workflows"][name]["steps"]


def all_catalog_names(catalog: dict) -> list[str]:
    return ["spine"] + sorted(catalog.get("workflows", {}))


# ---------------------------------------------------------------------------
# Verify against the runtime catalog
# ---------------------------------------------------------------------------

def verify(catalog: dict, runtime: dict) -> list[str]:
    """Return a list of mismatch strings; empty means a clean reproduction."""
    problems: list[str] = []
    rt_workflows = runtime.get("workflows", runtime)
    for name in all_catalog_names(catalog):
        rid = runtime_id(name)
        if rid not in rt_workflows:
            problems.append(f"{name}: runtime has no workflow '{rid}' to compare")
            continue
        derived = derive_steps(workflow_steps(catalog, name))
        rt_steps = rt_workflows[rid]["steps"]
        if len(derived) != len(rt_steps):
            problems.append(
                f"{name}->{rid}: step count {len(derived)} != runtime {len(rt_steps)}")
        for d, r in zip(derived, rt_steps):
            rn = str(r.get("n"))
            if d["n"] != rn:
                problems.append(f"{name}->{rid}: n {d['n']} != runtime {rn} (key {d['key']})")
            if d["key"] != r.get("key"):
                problems.append(f"{name}->{rid}: key {d['key']} != runtime {r.get('key')} at n={rn}")
            if d["label"] != r.get("label"):
                problems.append(
                    f"{name}->{rid}: label '{d['label']}' != runtime '{r.get('label')}' (key {d['key']})")
            if d["phase"] != r.get("phase"):
                problems.append(
                    f"{name}->{rid}: phase '{d['phase']}' != runtime '{r.get('phase')}' (key {d['key']})")
        derived_total = total_of(derived)
        rt_total = rt_workflows[rid].get("total")
        if rt_total is not None and derived_total != rt_total:
            problems.append(f"{name}->{rid}: total {derived_total} != runtime {rt_total}")
    return problems


# ---------------------------------------------------------------------------
# Overview
# ---------------------------------------------------------------------------

def overview(catalog: dict) -> str:
    lines = ["# Workflow Overview (generated)", "",
             "Derived from `tools/workflow-catalog/catalog.yaml`. Do not edit by hand.", ""]
    for name in all_catalog_names(catalog):
        derived = derive_steps(workflow_steps(catalog, name))
        lines.append(f"## {name} ({total_of(derived)} steps)")
        lines.append("")
        lines.append("| # | phase.step | label | key |")
        lines.append("|---|---|---|---|")
        for d in derived:
            lines.append(f"| {d['n']} | {d['phase_step']} | {d['label']} | {d['key']} |")
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Derive numbered views from the numberless catalog.")
    p.add_argument("mode", choices=["verify", "overview", "numbered"])
    p.add_argument("name", nargs="?", help="workflow name (for `numbered`)")
    p.add_argument("--catalog", default=str(DEFAULT_CATALOG))
    p.add_argument("--runtime", default=str(DEFAULT_RUNTIME))
    args = p.parse_args(argv)

    catalog = yaml.safe_load(Path(args.catalog).read_text())

    if args.mode == "verify":
        runtime = yaml.safe_load(Path(args.runtime).read_text())
        problems = verify(catalog, runtime)
        if problems:
            print(f"VERIFY FAILED: {len(problems)} mismatch(es)")
            for pr in problems:
                print(f"  - {pr}")
            return 1
        names = ", ".join(f"{n}->{runtime_id(n)}" for n in all_catalog_names(catalog))
        print(f"VERIFY OK: numberless catalog reproduces runtime for {names}")
        return 0

    if args.mode == "overview":
        print(overview(catalog))
        return 0

    if args.mode == "numbered":
        if not args.name:
            print("error: `numbered` needs a workflow name", file=sys.stderr)
            return 2
        for d in derive_steps(workflow_steps(catalog, args.name)):
            print(f"{d['n']:>3}  {d['phase_step']:<14} {d['label']:<10} {d['key']}")
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
