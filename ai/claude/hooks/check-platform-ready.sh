#!/usr/bin/env bash
# Production-deploy gate for the platform workflow (design: docs/design/platform-bootstrap/).
# Called by /hitl:ops-deploy as a pre-flight:  check-platform-ready.sh <environment> [tier]
#
# Exit 0 = deploy may proceed; exit 2 = blocked (reasons on stderr).
#
# Rules (decision D2, locked 2026-07-11 — hard block with waivers):
#   - Only PRODUCTION deploys are ever gated. Staging/canary/dev: always allowed
#     (the platform work itself needs them).
#   - Only Tier 2+ changes are gated. Tier comes from arg 2, else .hitl/current-change.yaml.
#   - No register file → allowed (projects predating the register are not retro-blocked;
#     onboarding creates it going forward).
#   - delivery_ready: true → allowed.
#   - Otherwise: allowed only if EVERY open item (status: gap) is covered by a waiver whose
#     tier_limit >= the change tier and whose revisit date has not passed. A lapsed waiver
#     counts as an open gap.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/_steps.sh"

ENVIRONMENT="${1:-}"
TIER_ARG="${2:-}"
REGISTER="docs/04-operations/platform-readiness.yaml"
CONTEXT_FILE=".hitl/current-change.yaml"

# Non-production targets are never gated.
case "$(printf '%s' "$ENVIRONMENT" | tr '[:upper:]' '[:lower:]')" in
  prod|production) ;;
  *) exit 0 ;;
esac

[[ -f "$REGISTER" ]] || exit 0  # no register — nothing to enforce

TIER="$TIER_ARG"
if [[ -z "$TIER" && -f "$CONTEXT_FILE" ]]; then
  TIER=$(hitl_scalar "$CONTEXT_FILE" tier || echo "")
fi
# Unknown tier is treated as Tier 2: a production deploy with no recorded tier does not
# get the low-tier bypass.
[[ "$TIER" =~ ^[0-9]+$ ]] || TIER=2
if (( TIER < 2 )); then
  exit 0
fi

PY=$(hitl_python) || exit 0  # no usable python — fail open, consistent with the other hooks

TODAY=$(date +%F)
export _HITL_REGISTER="$REGISTER" _HITL_TIER="$TIER" _HITL_TODAY="$TODAY"
"$PY" << 'PYEOF'
import os, sys
import re

path = os.environ["_HITL_REGISTER"]
tier = int(os.environ["_HITL_TIER"])
today = os.environ["_HITL_TODAY"]

try:
    import yaml
    data = yaml.safe_load(open(path)) or {}
except Exception:
    # Register unreadable as YAML: fall back to a conservative grep-style check.
    text = open(path, errors="replace").read()
    if re.search(r"^delivery_ready:\s*true\b", text, re.M):
        sys.exit(0)
    print("HITL DEPLOY BLOCKED: platform readiness register is not parseable and "
          "delivery_ready is not true.", file=sys.stderr)
    print(f"  Fix {path} or run /hitl:ops-plan-platform derive.", file=sys.stderr)
    sys.exit(2)

if data.get("delivery_ready") is True:
    sys.exit(0)

waivers = {}
for w in data.get("waivers") or []:
    item = str(w.get("item", ""))
    if item:
        waivers[item] = w

blockers = []
for layer, spec in (data.get("layers") or {}).items():
    for it in (spec or {}).get("items") or []:
        if it.get("status") != "gap":
            continue
        iid = str(it.get("id", "?"))
        w = waivers.get(iid)
        if w is None:
            blockers.append(f"{iid} ({layer}): {it.get('name','')} — open gap, no waiver")
            continue
        limit = w.get("tier_limit")
        if not isinstance(limit, int) or limit < tier:
            blockers.append(f"{iid} ({layer}): waiver tier_limit={limit} does not cover Tier {tier}")
            continue
        revisit = str(w.get("revisit", ""))
        if revisit and revisit < today:
            blockers.append(f"{iid} ({layer}): waiver lapsed (revisit {revisit})")

if not blockers:
    sys.exit(0)

print(f"HITL DEPLOY BLOCKED: platform is not delivery-ready (Tier {tier} production deploy).",
      file=sys.stderr)
for b in blockers:
    print(f"  • {b}", file=sys.stderr)
print("  Run /hitl:ops-plan-platform status for the full picture, or record waivers "
      "(owner + revisit + tier_limit) in the register.", file=sys.stderr)
sys.exit(2)
PYEOF
