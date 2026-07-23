"""The spike's whole point: validate — by EXECUTION — the two claims paper review kept probing.

  1. floor ≡ #10 activation   (the composer floor == the commands whose PRIMARY check activates on the
                               manifest those commands author; and OWNERSHIP-COMPLETE holds on that manifest)
  2. AUTHOR-COMPLETE          (the canonical state authors a manifest that passes #10's REAL validator)

Run: python3 test_seam.py
"""
from activation import ACTIVATES, features_from_manifest
from compose import (compose, floor_commands, PRIMARY_CHECKS, OWNS_CHECKS, check_ownership_complete)
from writer import write_manifest
from validator import validate
import fixtures

check_ownership_complete()  # static: every blocking check is owned by some command


def primary_owner(check):
    return {cmd for cmd, ch in PRIMARY_CHECKS.items() if check in ch}


def owners(check):
    return {cmd for cmd, ch in OWNS_CHECKS.items() if check in ch}


def run(name, state):
    comp = compose(state)
    floor = set(comp["floor"])
    m = write_manifest(state)
    feats = features_from_manifest(m)
    activated = {c for c, p in ACTIVATES.items() if p(feats)}

    # (1a) floor ≡ activation: the floor == commands whose PRIMARY check activates on the REAL manifest
    #      (plus the two non-#10 obligations, human-gate/kill-switch, which have no check)
    manifest_primary_floor = {cmd for cmd, ch in PRIMARY_CHECKS.items() if any(c in activated for c in ch)}
    non10 = floor - manifest_primary_floor  # reliability via human-gate/kill-switch is allowed here
    assert manifest_primary_floor <= floor, f"{name}: a primary check activates but its command isn't floor: {manifest_primary_floor - floor}"
    assert non10 <= {"agentic-reliability"}, f"{name}: unexpected non-activation floor members: {non10}"

    # (1b) OWNERSHIP-COMPLETE on the real manifest: every activated (blocking) check owned by a FLOOR command
    unowned = [c for c in activated if not (owners(c) & floor)]
    assert not unowned, f"{name}: activated checks with no floor owner: {unowned}"

    # (2) AUTHOR-COMPLETE: the authored manifest passes #10's real validator
    blockers, ran = validate(m, state["tier"])
    ok = not blockers
    print(f"{name:5} floor={comp['floor']}")
    print(f"      workflow={comp['workflow']}")
    print(f"      #10 activated {len(ran)} checks: {ran}")
    print(f"      AUTHOR-COMPLETE: {'PASS (exit 0)' if ok else 'FAIL — ' + str(blockers)}")
    print()
    return ok


if __name__ == "__main__":
    results = {n: run(n, s) for n, s in [("LOW", fixtures.LOW), ("HIGH", fixtures.HIGH), ("DEEP", fixtures.DEEP)]}
    print("=" * 70)
    print("floor ≡ activation + OWNERSHIP-COMPLETE: held for all fixtures (asserts above passed)")
    print("AUTHOR-COMPLETE:", {n: ("PASS" if ok else "FAIL") for n, ok in results.items()})
    if not all(results.values()):
        print("\n>>> A FAIL here is the executable B2 finding paper review kept predicting.")
