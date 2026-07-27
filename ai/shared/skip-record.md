# Shared skip-record schema

One dialect for recording a **skip** — a deliberate choice to lighten a step or control, kept as a durable,
neutral record. Used by both the **Agentic Design Advisor** (FR-28, per-control) and **First Pass** (FR-29,
per-workflow-step). Do not fork it (ADR-3).

## Fields

| field | required | meaning |
|-------|----------|---------|
| `step` (FR-29) / `control` (FR-28) | yes | the lightened workflow-step `key` or advisor control id |
| `crit` | yes (FR-29) | tier-resolved criticality: `ceremony \| standard \| floor` |
| `actor` / `owner` | yes | who chose (non-empty) |
| `reason` | yes | why, in neutral language (non-empty) |
| `ts` | yes | ISO-8601 timestamp |
| `disposition` | yes | `defer \| decline \| starter` |
| `followup_ref` | when `defer` | fast-follow ticket ref |
| `starter_artifact` | when `starter` | path to the `needs-enhancement` artifact |
| `waiver_ref` | when `floor` + hard gate | linked waiver id (skip ≠ waiver) |
| `ack_by` | when `floor` | accountable role that risk-accepted |
| `resolved` | — | true once the follow-up/enhancement lands |

## Invariants (enforced by the validators)

1. **Never silent.** A skipped step/control always has a record with non-empty `actor` + `reason` + a valid
   `disposition`. (Non-waivable.)
2. **Skip ≠ waiver.** A recorded skip grants no gate exception. A `floor` skip that maps to a fail-closed gate
   requires a linked `waiver_ref` (the waiver grants the exception); they are linked, never merged.
   (Non-waivable.)
3. **Floor needs authority.** A `floor` skip requires `ack_by` (the accountable role). (Non-waivable.)
4. **Honest starters.** A `starter` artifact is marked `needs-enhancement`, never presented as complete.

FR-29 enforcement: `ci/first-pass/check_skips.py`. FR-28 enforcement: `tools/agentic-advisor/records.py`
(`validate_skips`).
