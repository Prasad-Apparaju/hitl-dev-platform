# Validation review, lens: correctness, round 2

State under review: 1376a5edb108ae91a5fd77a2d3ab81a46b1fdeae (HEAD), `fix(review-gate): a failed check is answered by the finding that names it (#101 round 1)`.
Reviewer: clean context. Scratch records under `<scratch>/vr-round2/case-*/` (change.yaml = `change_id: GH-101`, `reviews/GH-101-round1.yaml`), each run as
`python3 ci/adversarial/check_review.py --root . --change <case>/change.yaml --reviews <case>/reviews --sha 1376a5e...`.

## Checklist

| # | Check | Result | Deciding output line |
|---|-------|--------|----------------------|
| 1 | Base 2.0 record | pass | `Release gate: verification review present, fresh, and cleared.` exit=0 |
| 2 | `result: fail` + finding F1 {class decide, check names it, accepted, accepted_by} + verified | pass | `Release gate: verification review present, fresh, and cleared.` exit=0 |
| 3 | As 2, finding has no `check:` | pass | `[BLOCK] VERDICT_CONTRADICTED: the round says 'verified' but 1 check(s) failed with no finding answering for them (GH-101-round1.yaml: install is 2.10.1)` exit=2 |
| 4 | As 2, `accepted` with no accepted_by | pass | `[BLOCK] UNSIGNED_ACCEPTANCE: ... findings[0] is accepted with no accepted_by` AND `[BLOCK] VERDICT_CONTRADICTED: ... 1 check(s) failed with no finding answering for them` exit=2 |
| 5 | As 2, `status: fixed, resolved_by: abc` | pass | `Release gate: verification review present, fresh, and cleared.` exit=0 |
| 6 | `result: fail`, findings [], verified | pass | `[BLOCK] VERDICT_CONTRADICTED: ... 1 check(s) failed with no finding answering for them (GH-101-round1.yaml: install is 2.10.1)` exit=2 |
| 7 | 1.0 record, F1 severity CRITICAL + class minor, open, verdict ship | pass | `[BLOCK] FINDING_OPEN: CRITICAL: x — fix it, or accept it explicitly with accepted_by` exit=2 (class ignored on 1.0) |
| 8 | 2.0, checks [{result: unknown}], findings [] | pass | `[warn] UNKNOWN_CHECK: GH-101-round1.yaml checks[0] could not be run (x). An unknown is not a pass.` then `[warn] SHALLOW_REVIEW: ... is round 1 with zero findings and no checks.` then `cleared.` exit=0 |
| 9 | schema_version "2026" | pass | `[BLOCK] WRONG_STANCE: ... stance must be 'refute'.` exit=2 (read as 1.0) |
| 10 | `python3 -m pytest ci/adversarial -q` / `python3 -m pytest ci/wiring -q -k "review or reviewer or lens or cost"` | pass | `62 passed, 1 skipped in 3.86s` (skip: `test_check_review.py:361: plugin repo not present`) / `5 passed, 229 deselected in 0.19s` |
| 11 | `grep -n 'round<N>'` over SKILL.md, verification-review.md, record template | pass | Record filenames: `verification-review.md:238`, `SKILL.md:204`, template line 1 all read `<change-id>-round<N>-<lens>.yaml`. The only lens-less hits are `SKILL.md:97` and `:121`, both the incoming report path `.hitl/reviews/incoming/<lens>-round<N>.md`, which is fine as stated. No record filename without the lens suffix. |

Eleven of eleven as expected. Two extra probes beyond the checklist, because the fix could have opened them:

- Probe A (two lens records, round 1): correctness record has `result: fail` and `findings: []`; bypass record has `result: pass` and the resolved, signed finding naming the check. Output: `Release gate: verification review present, fresh, and cleared.` exit=0. Coverage is pooled across all records in the round, not per record.
- Probe B: `status: fixed` with no `resolved_by` and no `verified_by`, naming the check. Output: `cleared.` exit=0.

## Points (ranked)

1. **worth deciding** — Coverage is round-wide, not per-record (probe A). `covered_checks` is one set over every record in `latest`, and `uncovered` compares on the check text alone, so lens B's fixed finding answers for lens A's failed check with the same text. Defensible if the check is the same fact, but it means a reviewer's own record can say `fail` with nothing answering for it and still clear. Decide whether that is the intent; the tests in `test_check_review.py` only cover the single-record case.
2. **worth deciding** — `status: fixed` covers a failed check with no `resolved_by` and no `verified_by` (probe B). The gate's own message says "fixed, or accepted with a name"; the accepted branch is signed (UNSIGNED_ACCEPTANCE) but the fixed branch requires nothing beyond the word. Same pre-existing looseness as FINDING_OPEN, now load-bearing for VERDICT_CONTRADICTED too.
3. **minor** — The record template (`ai/shared/templates/verification-review-record.yaml`, findings example lines 53-60) does not list a `check:` field on a finding, and `ai/shared/verification-review.md` never mentions it; the only prose is `SKILL.md:224`. A reviewer filling in the template will not know the field exists until VERDICT_CONTRADICTED tells them.
4. **minor** — Coverage matches on exact stripped text (case-sensitive, whitespace-internal). Not exercised here; noted because `check:` is free prose that the reviewer types twice.

Nothing in the **stops it working** class. The five round-1 points are resolved as claimed and the behaviours that were meant to be unchanged (6, 7, 8, 9) are unchanged.

## Verdict

VERIFIED.
