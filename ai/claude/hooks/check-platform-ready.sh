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
#   - delivery_ready is NEVER trusted as a bypass (2026-07-12 Codex round-6 note): the
#     gate re-derives readiness from the items and waivers themselves. The flag is the
#     recorded outcome; a register whose flag says true but whose items show open gaps
#     blocks as inconsistent. A hand-flipped flag releases nothing.
#   - Allowed only if the register has at least one item and EVERY open item
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
# is a blocker (2026-07-11 Codex rounds 2-3 — unknown statuses, incomplete waivers,
# duplicate/missing item ids, and unenforced migration layers must not fail open the way
# structural gaps did in round 1).
VALID_STATUSES = ("verified", "gap", "accepted_gap", "na")
VALID_KINDS = ("brownfield", "greenfield", "migration")
MIGRATION_ONLY_LAYERS = ("parity", "cutover")

# The canonical item set from platform-readiness-template.yaml (schema 1.0). The gate and
# the template ship together; a register missing canonical items is truncated or badly
# derived and cannot be positively validated (2026-07-11 Codex round 4). Teams may ADD
# items and layers freely; they may not lose these.
CORE_IDS = ("D1", "D2", "D3", "E1", "E2", "E3", "F1", "F2", "F3")
MIGRATION_IDS = ("P1", "P2", "C1", "C2", "C3")
# Canonical ids live in canonical layers (waivers join on id, but a canonical item filed
# under the wrong layer is a mis-derived register — 2026-07-12 round 5).
CANONICAL_LAYER = {"D": "verification", "E": "delivery", "F": "operation",
                   "P": "parity", "C": "cutover"}


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

    # The flag is DERIVED (template contract: "never hand-set"). It is never a bypass:
    # readiness is re-derived from the items and waivers below, so a hand-flipped
    # delivery_ready: true in an invalid or gapped register releases nothing
    # (2026-07-12 Codex round-6 note — the short-circuit skipped all validation).
    flag_ready = data.get("delivery_ready") is True

    waivers = {}
    duplicate_waivers = set()
    for w in data.get("waivers") or []:
        if isinstance(w, dict):
            item = str(w.get("item", ""))
            if item:
                if item in waivers:
                    duplicate_waivers.add(item)
                waivers[item] = w

    blockers = []
    total_items = 0

    # project_kind is a load-bearing field: it decides whether the migration-only layers
    # (parity, cutover) are enforceable. A register without a valid kind was never
    # properly derived and cannot be positively validated.
    kind = data.get("project_kind")
    if kind not in VALID_KINDS:
        blockers.append(f"register: project_kind {kind!r} is not valid (must be one of "
                        f"{', '.join(VALID_KINDS)}) — run /hitl:ops-plan-platform derive")

    schema = data.get("schema_version")
    if schema != "1.0":
        blockers.append(f"register: schema_version {schema!r} is not a version this gate "
                        "can validate (expected \"1.0\")")

    seen_ids = {}
    for layer, spec in (data.get("layers") or {}).items():
        for it in (spec or {}).get("items") or []:
            total_items += 1
            if not isinstance(it, dict):
                blockers.append(f"? ({layer}): item is not a mapping")
                continue
            raw_id = it.get("id")
            name = it.get("name", "")
            # Item identity is the waiver join key: it must exist and be unique. A
            # missing id is a schema violation, never a waivable "?" placeholder.
            if not isinstance(raw_id, str) or not raw_id.strip():
                blockers.append(f"? ({layer}): {name} — item has no id (ids are required "
                                "and are the waiver join key)")
                continue
            iid = raw_id.strip()
            if iid in seen_ids:
                blockers.append(f"{iid} ({layer}): duplicate item id (also in "
                                f"{seen_ids[iid]}) — waiver coverage would be ambiguous")
                continue
            seen_ids[iid] = layer
            expected_layer = (CANONICAL_LAYER.get(iid[0])
                              if iid in CORE_IDS + MIGRATION_IDS else None)
            if expected_layer and layer != expected_layer:
                blockers.append(f"{iid} ({layer}): canonical item is in the wrong layer "
                                f"(belongs in {expected_layer}) — the register is "
                                "mis-derived; re-run /hitl:ops-plan-platform derive")
                continue
            status = it.get("status")
            if status not in VALID_STATUSES:
                blockers.append(f"{iid} ({layer}): {name} — invalid status {status!r} "
                                f"(must be one of {', '.join(VALID_STATUSES)})")
                continue
            if status == "na":
                # The canonical D/E/F items are the four readiness pillars: they are
                # applicable by definition on every project kind. If one genuinely does
                # not apply in a given context, that is a recorded human decision — an
                # accepted_gap with a waiver — never a status flip to na.
                if iid in CORE_IDS:
                    blockers.append(f"{iid} ({layer}): {name} — na is not allowed for a "
                                    "canonical readiness item; record an accepted_gap "
                                    "with a waiver if it genuinely does not apply")
                # The migration-only items are APPLICABLE on a migration: leaving them
                # na would release a target whose parity/cutover was never proven.
                elif kind == "migration" and (iid in MIGRATION_IDS or layer in MIGRATION_ONLY_LAYERS):
                    blockers.append(f"{iid} ({layer}): {name} — na is not allowed on a "
                                    "migration register; derive real statuses for the "
                                    "Parity and Cutover layers")
                continue
            if status == "verified":
                evidence = it.get("evidence")
                if not isinstance(evidence, str) or not evidence.strip():
                    blockers.append(f"{iid} ({layer}): {name} — verified without evidence "
                                    "(the register contract requires evidence to verify)")
                continue
            # status is gap or accepted_gap: an adequate waiver is the only release.
            if iid in duplicate_waivers:
                blockers.append(f"{iid} ({layer}): multiple waiver entries for this item "
                                "— ambiguous; keep exactly one")
                continue
            w = waivers.get(iid)
            if w is None:
                kind_msg = "accepted_gap without a waiver" if status == "accepted_gap" else "open gap, no waiver"
                blockers.append(f"{iid} ({layer}): {name} — {kind_msg}")
                continue
            problem = waiver_problem(w, tier)
            if problem:
                blockers.append(f"{iid} ({layer}): {problem}")

    # FAIL CLOSED on a structurally empty register: no items means the register was
    # never derived (or was truncated). There is nothing to trust — whatever the flag says.
    if total_items == 0:
        lines = [f"HITL DEPLOY BLOCKED: platform readiness register has no items "
                 f"(Tier {tier} production deploy)."]
        if flag_ready:
            lines.append("  delivery_ready: true cannot be honored on an empty register "
                         "— the flag is derived from items that are not there.")
        lines.append("  Run /hitl:ops-plan-platform derive to populate it.")
        block(*lines)

    # Canonical completeness: a register missing canonical items is truncated or badly
    # derived — a plausible accident (partial write, merge mistake, wrong layer key) that
    # must not release production for lack of the very items that would have blocked it.
    required = list(CORE_IDS) + (list(MIGRATION_IDS) if kind == "migration" else [])
    missing = [rid for rid in required if rid not in seen_ids]
    if missing:
        blockers.append(f"register: canonical item(s) {', '.join(missing)} missing — the "
                        "register is incomplete; re-run /hitl:ops-plan-platform derive")

    if not blockers:
        sys.exit(0)

    if flag_ready:
        blockers.insert(0, "register: delivery_ready: true contradicts the findings below "
                           "— the flag is derived, never hand-set; re-run "
                           "/hitl:ops-plan-platform verify-ready")

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
