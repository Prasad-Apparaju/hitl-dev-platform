# Verification review — lens: bypass — GH-101 round 1

**Reviewed:** 1d20e4b3585683b96179add79b0b5c29ab43f3f0 (`ci/adversarial/check_review.py`, `ai/shared/templates/verification-review-record.yaml`), diff from 143c864.
**Claim:** a 2.0 record cannot pass the gate more easily than a 1.0 record could.
**Reviewer:** clean context, no history of building this change.
**Method:** each record built under `scratchpad/vr-bypass/case-*/` (`change.yaml` = `{change_id: GH-101}`, `reviews/GH-101-round1.yaml`), then
`python3 ci/adversarial/check_review.py --root . --change <case>/change.yaml --reviews <case>/reviews --sha 1d20e4b3585683b96179add79b0b5c29ab43f3f0`
from the repo root, working tree clean (`git status --short | wc -l` = 0). Harness: `scratchpad/vr-bypass/harness.py`.

## The ten checks

| # | Record variant | Expected | Exit | Deciding output line |
|---|---|---|---|---|
| 1 | base 2.0 record | 0 | **0** | `Release gate: verification review present, fresh, and cleared.` |
| 2 | `reviewer.context: inherited` | NOT_INDEPENDENT | **2** | `[BLOCK] NOT_INDEPENDENT: ... reviewer.context must be 'clean'` |
| 3 | `reviewed_sha` = 143c864 (parent) | REVIEW_STALE | **2** | `[BLOCK] REVIEW_STALE: ... reviewed 143c8642feb5 but 1d20e4b35856 is about to ship — CHANGELOG.md, ... changed since (+26 more)` |
| 4a | finding `class: stops`, open | FINDING_OPEN | **2** | `[BLOCK] FINDING_OPEN: stops: x — fix it, or accept it explicitly with accepted_by` |
| 4b | finding `class: decide`, open | FINDING_OPEN | **2** | `[BLOCK] FINDING_OPEN: decide: x — ...` |
| 4c | finding `class: minor`, open | 0 | **0** | `Release gate: ... cleared.` (no warning) |
| 5 | `class: decide`, `status: accepted`, no `accepted_by` | UNSIGNED_ACCEPTANCE | **2** | `[BLOCK] UNSIGNED_ACCEPTANCE: ... findings[0] is accepted with no accepted_by` |
| 6 | `checks: []`, `findings: []`, verdict verified | record | **0** | `[warn] NO_CHECKS: ... empty checks table` + `[warn] SHALLOW_REVIEW: ... zero findings and no checks` |
| 7a | 2.0 with `stance: confirm` | record | **0** | cleared, no warning (stance ignored on 2.0) |
| 7b | 2.0 with no stance | record | **0** | cleared |
| 7c | 1.0, stance omitted, findings [], verdict ship | WRONG_STANCE | **2** | `[BLOCK] WRONG_STANCE: ... stance must be 'refute'` (+ SHALLOW_REVIEW warn) |
| 8 | 2.0, finding `severity: CRITICAL`, open, no `class` | record | **2** | `[BLOCK] FINDING_OPEN: CRITICAL: x — fix it, or accept it explicitly` (severity path still blocks under 2.0) |
| 9 | 2.0 with `verdict: ship` | record | **0** | cleared; also 1.0 with `verdict: verified` → exit 0 (case I). Not a hole: both words are in PASS_VERDICTS and neither is weaker than the other; the vocabulary carries no gate strength by itself |
| 10 | check `result: fail`, findings [], verdict verified | VERDICT_CONTRADICTED | **2** | `[BLOCK] VERDICT_CONTRADICTED: the round says 'verified' but 1 check(s) failed (GH-101-round1.yaml: a)` |

Extra probes (same command, records under `case-A1`, `case-A2`, `case-C`, `case-G1..G3`, `case-H`, `case-J`, `case-K`):
- A1 1.0 record, finding `severity: CRITICAL` + `class: minor`, open → exit 0, no warning. A2 same on 2.0 → exit 0.
- C 2.0, `checks: [{result: unknown}]`, findings [] → exit 0, only `[warn] UNKNOWN_CHECK`; SHALLOW_REVIEW not printed.
- G1 `result: fail` + finding `class: stops, status: accepted, accepted_by: someone` → exit 2 VERDICT_CONTRADICTED. G2 same with `status: fixed, resolved_by` → exit 2 VERDICT_CONTRADICTED. G3 same as G1 with `result: unknown` → exit 0.
- J `schema_version: "2026"` → treated as 2.0 (`startswith("2")`), exit 0.
- K 2.0 with no `checks` key at all → exit 0, NO_CHECKS + SHALLOW_REVIEW (same as check 6).

## Points, ranked

1. **worth deciding** — VERDICT_CONTRADICTED cannot be resolved the way its own message says. `elif failed_checks:` fires on any `result: fail` in the round regardless of findings (line ~540), so a failed check that IS recorded as a finding and accepted by name (G1) or marked fixed (G2) still blocks. The only records that pass are ones where the reviewer rewrites `fail` to `unknown` (G3, exit 0 with a warning) or `pass`. That does not make a 2.0 record pass more easily than 1.0, but it pushes the honest record toward a false field, the pattern the file header (line ~95) says it exists to avoid. Someone should decide whether an accepted-by-name failed check is a verified round or not; the code and the message currently disagree.
2. **minor** — `class` overrides `severity` whenever both are present, in either schema (`if "class" in f or ...`). A 1.0 record with `severity: CRITICAL, class: minor, status: open` passes with no block and no warning (A1); before this commit it blocked FINDING_OPEN. This is the same author's attestation either way (they could have written LOW), so no independence is lost, but two contradicting grades on one finding go unremarked.
3. **minor** — check 6: `verified` with zero checks and zero findings passes (exit 0, NO_CHECKS + SHALLOW_REVIEW). This is the same posture the 1.0 zero-findings record had (warn, exit 0), so it is not a new way past. What is slightly quieter than 1.0: a table of only `unknown` results counts as "ran checks" and suppresses SHALLOW_REVIEW (C), so one `unknown` row plus nothing else yields a single warning where 1.0 yielded SHALLOW_REVIEW.
4. **minor** — `stance` on a 2.0 record is ignored (7a: `stance: confirm` passes silently). Consistent with the 2.0 template having no stance field; the record's promise is now the checks table. Not a bypass, noted for completeness.
5. **minor** — `schema_version` detection is `str(...).startswith("2")`, so `"2026"` or `"21"` reads as 2.0 (J). No practical bypass (a 2.0 record is not weaker than 1.0), just loose.

## Verdict

**VERIFIED.** All ten checklist items behaved as expected; independence (2), freshness (3), signed acceptance (5), open blocking findings (4a/4b/8) and failed-check contradiction (10) all block a 2.0 record exactly as the 1.0 rules did, and severity-graded findings still block under 2.0. Nothing found lets a 2.0 record pass the gate more easily than a 1.0 record. Point 1 is a decision, not a bypass.
