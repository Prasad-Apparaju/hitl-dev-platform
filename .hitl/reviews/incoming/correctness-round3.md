# Correctness review, round 3: HITL 2.14.0 at 2de5aee

**Verdict: verified.** All round-1 findings are fixed or accepted with evidence; every number on both live pages is inside an anchor; the three gates pass at the fix commit.

## Checks

| # | Check | Command | Result | Output |
|---|---|---|---|---|
| 1 | Diff scope | `git diff --stat 66304b1..2de5aee` | pass | 8 files: `tools/team-pulse/pulse.py` (+30/-?), `tools/team-pulse/test_pulse.py` (+21), `ai/claude/skills/team-pulse/SKILL.md` (2), `CHANGELOG.md` (2), and four records under `.hitl/reviews/` (three incoming reports plus `GH-139-release-2.14.0-round1-upgrade.yaml`). Nothing else. |
| 2 | Pulse tests | `python3 -m pytest tools/team-pulse -q` | pass | `13 passed in 0.06s`, exit 0. `test_every_number_on_the_page_is_a_link` at test_pulse.py:137 walks every number on both audiences and asserts an open `<a ` precedes it with no `</a>` in between; also asserts `commits?author=ann`, `1/4 slices done</a>`, and `review-requested%3Abob` on leads. |
| 3 | Live render | `pulse.py collect --out data.json --config /nonexistent --repo Prasad-Apparaju/hitl-dev-platform`; `render ... --audience team`; `render ... --audience leads` | pass | collect: `3 people, 2 epics, 3 attention items`, exit 0; both renders exit 0. Anchor scan (same rule as the test) over the whole page: team.html 10 numbers, 0 unlinked; leads.html 16 numbers, 0 unlinked. Tally line: `<a href=".../commits?author=pappar">32 commits</a> · <a href=".../pulls?q=is%3Apr+author%3Apappar">1 PRs opened</a> · <a href=".../pulls?q=is%3Apr+is%3Amerged+author%3Apappar">1 merged</a> · ...`. Slice count: `<a href=".../issues/22">1/9 slices done</a> · owner none`. |
| 4 | Gates | `python3 -m pytest ci/ tools/ -q`; `python3 ci/skill-lint/check_skills.py`; `(cd tools/workflow-catalog && python3 derive.py verify)` | pass | `1154 passed in 68.06s` exit 0; `Skill lint: 64/64 files pass all hard gates; 0 failures, 0 warnings.` exit 0; `VERIFY OK: numberless catalog reproduces runtime for ...` exit 0. |
| 5 | $ROOT line | `diff` of the `ROOT=` line in `ai/claude/skills/team-pulse/SKILL.md` against the (single distinct) `ROOT=` line in `ai/claude/start-change/SKILL.md` | pass | identical byte for byte, including the `.claude-plugin/plugin.json` isfile filter. |
| 6 | Changelog | `grep -n "docs corrected" CHANGELOG.md` | pass | line 32: `... Four docs corrected.` |

## Round-1 findings

| Claim (verbatim) | Status | Evidence |
|---|---|---|
| "Every number and event links to its GitHub source" | fixed | Live team and leads pages: 0 unlinked numbers (check 3); pulse.py links tallies to GitHub search URLs, the slice count to the epic issue; new test test_pulse.py:137 enforces it for both audiences. |
| the skill's `$ROOT` line "is the same shape as in start-change Step 6b" | fixed | Lines identical (check 5). |
| "Three docs corrected." | fixed | CHANGELOG.md:32 now reads "Four docs corrected." matching the four docs in 8ba3118. |
| "the attention strip lists exactly the epics with a flag and the PRs past the thresholds" | fixed | test_pulse.py:191-192 now asserts `pr_items == {"PR #20 needs a reviewer (5d)", "Draft PR #21 idle 16d", "PR #22 merged by its author with no review"}` as a set, alongside the epic set equality. |
| "Decision recorded on #112 and plugin #34." | accepted | Lead supplied the plugin #34 comment URL (pappar/hitl-claude-plugin#34, issuecomment-5747448847); my round-1 query used the wrong repo slug. Not re-fetched this round. |

## New findings

Nothing failed. One note, not a finding: the number-link test and my scan treat a bare `—` as the only allowed unlinked value; a future tally that renders `0` as plain text would fail the test, which is the intended direction.
