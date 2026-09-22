# Correctness review, round 1: HITL 2.14.0 (66304b1)

**Verdict: verified, with one claim to decide.** Every gate, test and end-to-end run passed as claimed; the one gap is that per-person tallies and epic slice counts on the Team Pulse page are plain text, so "Every number and event links to its GitHub source" is carried for events only.

## Checks

| # | Check | Command | Result | Output |
|---|---|---|---|---|
| 1 | Gates | `python3 -m pytest ci/ tools/ -q` | pass | `1153 passed in 73.77s`, exit 0 |
| 1 | Skill lint | `python3 ci/skill-lint/check_skills.py` | pass | `Skill lint: 64/64 files pass all hard gates; 0 failures, 0 warnings.`, exit 0 |
| 1 | Catalog | `(cd tools/workflow-catalog && python3 derive.py verify)` | pass | `VERIFY OK: numberless catalog reproduces runtime for spine->development, ...`, exit 0 |
| 2 | Pulse tests | `python3 -m pytest tools/team-pulse -q` | pass | `12 passed in 0.05s`, exit 0. Acceptance mapping below. |
| 3 | Pulse live | `pulse.py collect --out data.json --config /nonexistent --repo Prasad-Apparaju/hitl-dev-platform` / `notes` / `render` team / `render` leads | pass | collect: `team-pulse: 3 people, 2 epics, 3 attention items -> data.json` exit 0; notes exit 0 (JSON with empty strings and the facts-only rule); render team exit 0 `wrote team.html (team); 3 attention items`; render leads exit 0. `Planning (leads only)`: 0 in team.html, 1 in leads.html. 27 distinct `<a href` in team.html, 0 missing from leads.html. `<script`: 0; `src="`: 0; `@import`: 0. Strip on page = the 3 printed items (`Epic #22: no owner`, `Epic #105: no owner`, `Epic #105: no checkbox list`). |
| 4 | Skill vs CLI | `pulse.py {collect,notes,render} --help` vs `ai/claude/skills/team-pulse/SKILL.md` | pass with note | Skill uses `collect --out`, `notes --data`, `render --data --notes --audience`; all exist (collect: `--config --out --repo --window-days`; notes: `--data`; render: `--audience --config --data --notes --out`). Skill omits `--out` on render; generator defaults to `docs/04-operations/team-pulse.html` or `team-pulse-leads.html` (pulse.py:576), matching the skill's prose. `$ROOT` line differs from start-change Step 6b (see finding 2). Nothing the skill asks that the generator cannot do. |
| 5 | Skipped line | `gen_change.py development GH-321 issue/321-x 2.14.0 2 choices.json "" ""`; `check_skips.py`; `skipped_line.py --change ... --apply` x3; reason injected with `<!-- /hitl:skipped -->`, x3 | pass | Defer entry carries `followup_ref: "issue:321"`. check_skips: `First Pass skip ledger: clean.` exit 0. Apply: `skipped line written` / `unchanged` / `unchanged`, all exit 0, one open and one close marker. After injection: `written` / `unchanged` / `unchanged`, still one open and one close marker; the injected close marker is neutralised to `/hitl:skipped` inside the line. Note: the choices file key is `disposition`, not `choice`; a wrong key fails fast with a clear message. |
| 6 | #136 grep | `grep -rn -i "created by \`/hitl:\(dev-\)\?apply-change\|apply-change.*to initiali" ai/claude docs --include=*.md \| grep -v session-logs` | pass | empty (grep exit 1) |
| 6 | #136 wiring | `python3 -m pytest ci/wiring/test_wiring.py -q -k apply_change` | pass | `2 passed, 57 deselected`, exit 0 |
| 7 | Claim carriers | grep | pass | table below |
| 8 | PRD | grep `docs/01-product/prd.md` | pass | FR-32 occurs once (line 103), in §5.4 (line 95), directly after FR-16 (line 102), table has `Acceptance Criteria` column (line 97); not in §5.7 (line 128). FR-33 line 139 and FR-34 line 140 are in §5.7. |
| 9 | Plain English | `python3 -m pytest ci/wiring/test_plain_english.py -q` | pass | `16 passed in 0.22s`, exit 0 |

### Check 2: acceptance items asserted by `tools/team-pulse/test_pulse.py`

| Item | Asserted? | Where |
|---|---|---|
| (a) one run, no manual edits | partly | `test_cli_end_to_end_writes_data_notes_and_page` runs collect/notes/render and checks a page exists; nothing asserts "no manual edits" beyond `test_notes_render_as_facts_and_missing_notes_leave_no_placeholder`. |
| (b) every event and number links | events only | `test_every_event_links_to_its_source` asserts every event has an https URL. No test asserts a number (tally or slice count) links. |
| (c) strip exactly flags + threshold PRs | epics exact, PRs one-sided | `test_attention_strip_is_exactly_flags_and_threshold_breaches`: epic items `== flagged` set; PR items checked with `any(...)` for three expected entries, no assertion that no other PR item appears. |
| (d) hook/gate comments never human | yes | `test_collect_uses_gh_only_and_drops_bots_and_hook_comments` |
| (e) valid `Hours:` bar, invalid ignored | yes | `test_hours_line_valid_renders_bar_and_invalid_is_ignored` |
| (f) leads section never on team; team subset of leads | yes | `test_leads_section_never_reaches_team_page_and_team_is_a_subset` |
| (g) `publish: file` works without Artifact | not asserted | No test reads `publish`; the generator never touches an Artifact tool, so the CLI e2e test is the nearest evidence. `publish` is a skill-level key (pulse.py:37 default `file`). |

### Check 7: claim carriers

| Claim (first sentence, verbatim) | Carrier |
|---|---|
| **Team Pulse** (#118, FR-32): `/hitl:team-pulse` writes one page from GitHub that shows who is on what, what is waiting on someone else, and who can unblock it. | `ai/claude/skills/team-pulse/SKILL.md:4-5,28`; `ai/shared/team-pulse.md:4`; `docs/team-pulse.md:4-5`; `docs/01-product/prd.md:103`. "12 tests": verified (12). "Every number and event links": events yes, numbers no (finding 1). |
| **`dev-switch-context` and `impact-brief` no longer send people to `dev-apply-change` to create a branch or change file** (#136). | `ai/claude/switch-context/SKILL.md:63,71`; `ai/claude/impact-brief/SKILL.md:29`; wiring test `ci/wiring/test_wiring.py:838` `test_no_skill_sends_people_to_apply_change_to_create_a_branch_or_change_file`. "Three docs corrected": commit 8ba3118 touches four docs plus requirements (finding 3). |
| **A skipped step is one line at the top of the issue, not a ticket each.** | `ai/claude/start-change/SKILL.md:311,433-462` (Step 6b, `skipped_line.py`); `ci/first-pass/skipped_line.py` (run, check 5); `ci/first-pass/gen_change.py:245` (`followup_ref`); hygiene test `ci/wiring/test_wiring.py:818`; `docs/01-product/first-pass/requirements.md:112` (CR-7 amended); `docs/design/first-pass/03-lld.md:161` (§6.1). Decision on #112: found (comment dated 2026-09-19). Plugin #34: not verified, the query returned nothing. |

## Findings

1. `decide` **Claim:** "Every number and event links to its GitHub source". **Evidence:** live team.html renders `<p class='tally'>32 commits · 1 PRs opened · 1 merged · 30 comments · 16 issues opened</p>` and `<span class='tally'>1/9 slices done · owner none</span>` (pulse.py:485) with no anchor; the only test on links covers events. PRD FR-32 acceptance says "every event and number links". **Cost if it ships:** the changelog and PRD overstate; a reader cannot click a tally to check it. Either link the tallies or narrow the claim to events.

2. `minor` **Claim:** the skill's `$ROOT` line "is the same shape as in start-change Step 6b". **Evidence:** `ai/claude/skills/team-pulse/SKILL.md:40` lacks the `if os.path.isfile(os.path.join(i.get('installPath',''),'.claude-plugin/plugin.json'))` filter that `ai/claude/start-change/SKILL.md:344,450` carries. **Cost:** with a stale entry in installed_plugins.json the skill can resolve to a dead install path and report "generator not found".

3. `minor` **Claim:** "Three docs corrected." **Evidence:** `git show --stat 8ba3118` lists `docs/playbook/adoption-guide.md`, `docs/playbook/process-overview.md`, `docs/roles/developer.md`, `docs/usage-guide.md` and `docs/01-product/branch-context/requirements.md`. **Cost:** count in the changelog is off by one or two; no behavioural effect.

4. `minor` **Claim:** "the attention strip lists exactly the epics with a flag and the PRs past the thresholds" (FR-32 acceptance). **Evidence:** the test asserts set equality for epics but only presence for the three PR items; a fourth, wrong PR item would pass. Live run had no PR items to compare. **Cost:** the "exactly" half for PRs rests on reading `derive`, not on a test.

5. `minor` **Claim:** "Decision recorded on #112 and plugin #34." **Evidence:** #112 comment found; plugin #34 not confirmed by `gh issue view 34 --repo Prasad-Apparaju/hitl` (empty result, repo slug may differ). **Cost:** none if the comment exists; unverified here.

Nothing failed.
