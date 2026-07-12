#!/usr/bin/env bash
# Production-deploy gate for the platform workflow (design: docs/design/platform-bootstrap/).
# Called by /hitl:ops-deploy as a pre-flight:  check-platform-ready.sh <environment> [tier]
#
# Exit 0 = deploy may proceed; exit 2 = blocked (reasons on stderr).
#
# Rules (decision D2, locked 2026-07-11 — hard block with waivers; hardened per the
# 2026-07-11 Codex validation, which found fail-open paths):
#   - Only PRODUCTION deploys are ever gated. Staging/canary/dev: always allowed
#     (the platform work itself needs them).
#   - Only Tier 2+ changes are gated. Tier comes from arg 2, else .hitl/current-change.yaml.
#   - No register file → allowed (projects predating the register are not retro-blocked;
#     onboarding creates it going forward).
#   - delivery_ready: true (in a PARSEABLE register) → allowed.
#   - Otherwise: allowed only if the register has at least one item and EVERY open item
#     (status gap OR accepted_gap) is covered by a waiver whose tier_limit >= the change
#     tier and whose revisit date has not passed. A lapsed waiver counts as an open gap.
#   - FAIL CLOSED when the gate cannot evaluate: no PyYAML-capable python, unparseable
#     register, or a register with zero items. A hard gate that cannot read its input
#     blocks; it never guesses.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/_steps.sh"

ENVIRONMENT="${1:-}"
TIER_ARG="${2:-}"
REGISTER="docs/04-operations/platform-readiness.yaml"
CONTEXT_FILE=".hitl/current-change.yaml"

# Non-production targets are never gated. Trim whitespace before matching so a
# user-entered "Production " cannot slip past the gate.
ENV_NORM="$(printf '%s' "$ENVIRONMENT" | tr '[:upper:]' '[:lower:]' | tr -d '[:space:]')"
case "$ENV_NORM" in
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

# Find a python that can actually parse the register (import yaml, not just import sys —
# hitl_python's probe is too weak for this gate). $HITL_PY is honored first. No capable
# interpreter → FAIL CLOSED: this is a hard gate; it does not guess.
PY=""
for cand in "${HITL_PY:-}" python3 python py; do
  [[ -n "$cand" ]] || continue
  if command -v "$cand" >/dev/null 2>&1 && "$cand" -c "import yaml" >/dev/null 2>&1; then
    PY="$cand"
    break
  fi
done
if [[ -z "$PY" ]]; then
  echo "HITL DEPLOY BLOCKED: no Python with PyYAML found, so the platform readiness register cannot be verified." >&2
  echo "  Install PyYAML (pip install pyyaml) or set HITL_PY to a capable interpreter, then retry." >&2
  echo "  A Tier ${TIER} production deploy is not allowed on an unverifiable register." >&2
  exit 2
fi

TODAY=$(date +%F)
export _HITL_REGISTER="$REGISTER" _HITL_TIER="$TIER" _HITL_TODAY="$TODAY"
"$PY" << 'PYEOF'
import datetime
import os, sys
import yaml

path = os.environ["_HITL_REGISTER"]
tier = int(os.environ["_HITL_TIER"])
today = os.environ["_HITL_TODAY"]

# The gate validates SCHEMA, not just structure: anything it cannot positively validate
# is a blocker (2026-07-11 Codex round 2 — unknown statuses and incomplete waivers must
# not fail open the way structural gaps did in round 1).
VALID_STATUSES = ("verified", "gap", "accepted_gap", "na")


def block(*lines):
    for line in lines:
        print(line, file=sys.stderr)
    sys.exit(2)


def waiver_problem(w, tier):
    """Return why this waiver cannot release a Tier `tier` deploy, or None if adequate.
    The register contract (template header) requires owner + revisit + tier_limit + reason."""
    limit = w.get("tier_limit")
    if isinstance(limit, bool) or not isinstance(limit, int):
        return f"waiver tier_limit={limit!r} is not an integer"
    if limit < tier:
        return f"waiver tier_limit={limit} does not cover Tier {tier}"
    owner = w.get("owner")
    if not isinstance(owner, str) or not owner.strip():
        return "waiver has no owner"
    revisit = w.get("revisit")
    if isinstance(revisit, datetime.date):
        revisit = revisit.isoformat()
    if not isinstance(revisit, str) or not revisit.strip():
        return "waiver has no revisit date"
    try:
        datetime.date.fromisoformat(revisit)
    except ValueError:
        return f"waiver revisit {revisit!r} is not a valid YYYY-MM-DD date"
    if revisit < today:
        return f"waiver lapsed (revisit {revisit})"
    reason = w.get("reason")
    if not isinstance(reason, str) or not reason.strip():
        return "waiver has no reason"
    return None


try:
    try:
        data = yaml.safe_load(open(path)) or {}
        if not isinstance(data, dict):
            raise ValueError("register is not a mapping")
    except Exception:
        # FAIL CLOSED: an unparseable register never releases a production deploy,
        # whatever text it happens to contain.
        block("HITL DEPLOY BLOCKED: platform readiness register is not parseable.",
              f"  Fix {path} or re-run /hitl:ops-plan-platform derive.")

    if data.get("delivery_ready") is True:
        sys.exit(0)

    waivers = {}
    for w in data.get("waivers") or []:
        if isinstance(w, dict):
            item = str(w.get("item", ""))
            if item:
                waivers[item] = w

    blockers = []
    total_items = 0
    for layer, spec in (data.get("layers") or {}).items():
        for it in (spec or {}).get("items") or []:
            total_items += 1
            if not isinstance(it, dict):
                blockers.append(f"? ({layer}): item is not a mapping")
                continue
            iid = str(it.get("id", "?"))
            status = it.get("status")
            name = it.get("name", "")
            if status not in VALID_STATUSES:
                blockers.append(f"{iid} ({layer}): {name} — invalid status {status!r} "
                                f"(must be one of {', '.join(VALID_STATUSES)})")
                continue
            if status == "na":
                continue
            if status == "verified":
                evidence = it.get("evidence")
                if not isinstance(evidence, str) or not evidence.strip():
                    blockers.append(f"{iid} ({layer}): {name} — verified without evidence "
                                    "(the register contract requires evidence to verify)")
                continue
            # status is gap or accepted_gap: an adequate waiver is the only release.
            w = waivers.get(iid)
            if w is None:
                kind = "accepted_gap without a waiver" if status == "accepted_gap" else "open gap, no waiver"
                blockers.append(f"{iid} ({layer}): {name} — {kind}")
                continue
            problem = waiver_problem(w, tier)
            if problem:
                blockers.append(f"{iid} ({layer}): {problem}")

    # FAIL CLOSED on a structurally empty register: no items + not delivery-ready means
    # the register was never derived (or was truncated). There is nothing to trust.
    if total_items == 0:
        block(f"HITL DEPLOY BLOCKED: platform readiness register has no items and "
              f"delivery_ready is not true (Tier {tier} production deploy).",
              "  Run /hitl:ops-plan-platform derive to populate it.")

    if not blockers:
        sys.exit(0)

    print(f"HITL DEPLOY BLOCKED: platform is not delivery-ready (Tier {tier} production deploy).",
          file=sys.stderr)
    for b in blockers:
        print(f"  • {b}", file=sys.stderr)
    print("  Run /hitl:ops-plan-platform status for the full picture, or record complete "
          "waivers (owner + revisit + tier_limit + reason) in the register.", file=sys.stderr)
    sys.exit(2)
except SystemExit:
    raise
except Exception as exc:  # FAIL CLOSED on anything unexpected — never crash into a deploy
    block("HITL DEPLOY BLOCKED: platform readiness register could not be evaluated "
          f"({type(exc).__name__}).",
          f"  Fix {path} or re-run /hitl:ops-plan-platform derive.")
PYEOF
