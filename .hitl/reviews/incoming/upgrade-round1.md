# Adversarial review — lens: upgrade — round 1

State under review: `7a123555727f92e8dc1ae3595249a552ec334dcb` (main), diff `v2.7.1..HEAD`, 25 files.
Stance: refute. Every finding below was reproduced; the command and observed output are inline.

Working repo left untouched except this file. All fixtures under `mktemp -d` scratch dirs.

---

## Summary

| # | Sev | Finding |
|---|---|---|
| F1 | HIGH | The rewritten branch-mismatch hook message prints an empty branch name and tells you to switch to `''`. New in 2.8.0; 2.7.1 was correct. |
| F2 | HIGH | Records that passed the gate on 2.7.1 now block on two new rules. The CHANGELOG's "Note for existing projects" asserts the opposite. |
| F3 | HIGH | The only escape `LENS_FLOOR` names discards the review entirely — three real records become "no adversarial review was honoured". |
| F4 | HIGH | Both new release-only rules are OFF for this release: `.hitl/current-change.yaml` at HEAD says `workflow.id: development`. The gate prints "cleared" on one lens plus an unverified CRITICAL. |
| F5 | HIGH | `adversarial-review/SKILL.md` says "Do not give the reviewers names" at line 94 and "Give each reviewer a distinct name" at line 140 — the last line of the same step. Naming is the defect this release exists to fix. |
| F6 | MEDIUM | `LENS_FLOOR` counts distinct *strings*, not catalog lenses. Two invented names satisfy it; a name that canonicalises to the empty string counts as a lens. |
| F7 | MEDIUM | `canonical_lens()` strips a bare trailing `b` and bare trailing digits with no separator required. `costb` → `cost` lands in a real catalog bucket; `ipv4`/`ipv6` and `api-v1`/`api-v2` collapse into one. |
| F8 | MEDIUM | `functionality` → `fitness` is an undocumented fifth alias, and it buckets a code question into the design lens. The mirror test only checks one direction. |
| F9 | MEDIUM | The portal ships "current release: v2.7.1" on four pages in the commit that publishes 2.8.0 — in the release whose own notes call the stale portal a defect it fixed. |
| F10 | MEDIUM | `/hitl:dev-preferences` claims *"Plain text" turns them off*. No hook reads any preference; all 42 rewritten messages keep their glyphs. |
| F11 | LOW | The icon vocabulary is documented as four glyphs; the same release ships 🔄 and 📝. |
| F12 | LOW | Brief item 7 says "Say it last so it is the instruction nearest the end of the brief" and is item 7 of 8. |

---

## F1 — HIGH — the mismatch message tells you to switch to `''`

`ai/claude/hooks/check-hitl-context.sh:151-154`. The rewrite added `${EXPECTED}` to the else branch,
which the 2.7.1 message did not reference. `EXPECTED` comes from `hitl_scalar "$f" expected_branch`
(line 141) — but `hitl_branch_reconcile` (`_steps.sh:228`) also returns `mismatch` down its **second**
path, where there is no `expected_branch` at all and the issue number is derived from an `issue/N-*`
branch name. On that path `EXPECTED` is the empty string, and `hitl_branch_gone` returns 1 (it requires
a non-empty expected), so control lands in exactly the branch that now interpolates it.

Fixture: change file with `change_id: GH-7` and **no** `expected_branch`, on branch `issue/42-something`.

```
$ echo '{"tool_name":"Edit","tool_input":{"file_path":"src.py"}}' \
    | CLAUDE_PROJECT_DIR="$T" bash hooks/check-hitl-context.sh
🧭 You are on 'issue/42-something', but the tracked change GH-7 lives on ''.

Edits are paused until those agree, so pick whichever is true:
  • Working on GH-7? Switch to ''.
  • Working on something else here? /hitl:dev-switch-context points HITL at this branch.
  • Starting something new? /hitl:dev-start-change.
EXIT=2
```

Same fixture, 2.7.1's hook:

```
$ echo '{"tool_name":"Edit","tool_input":{"file_path":"src.py"}}' \
    | CLAUDE_PROJECT_DIR="$T" bash oldhooks/check-hitl-context.sh
HITL CONTEXT MISMATCH: branch 'issue/42-something' does not match active change GH-7.
All edits are blocked until the context is realigned.
  • Run /hitl:dev-switch-context to reload context for this branch.
  • Or run /hitl:dev-start-change to select the correct change.
EXIT=2
```

This is a hard block on every edit, and the first two of three remedies are now unreadable. The
release note for this work is "HITL stops talking like a compiler"; on this path it stopped saying
anything. Change files without `expected_branch` are not exotic — the second reconcile path exists
precisely because they are the older shape.

**Fix:** in the else branch, use `${EXPECTED:-<not recorded>}`, or branch on `[[ -n "$EXPECTED" ]]`
and fall back to the 2.7.1 wording.

Verified no other regression of this class: for all five hooks, every line that is not an `echo`
or a comment is byte-identical to v2.7.1 (one indentation change in a `- $p` list item excepted),
and `bash -n` passes on all five.

```
$ for f in check-domain-boundary.sh check-hitl-context.sh check-platform-ready.sh rebuild-graph.sh write-session-summary.sh; do
    bash -n ai/claude/hooks/$f && diff <(git show v2.7.1:ai/claude/hooks/$f | grep -vE '^\s*echo|^\s*#') \
                                       <(grep -vE '^\s*echo|^\s*#' ai/claude/hooks/$f); done
# only: 106c106  "    - $p"  ->  "     - $p"
```

`TIER` (check-platform-ready, defaulted to 2 at line 52), `CHANGE_ID`/`ALLOWED_PATHS`/`IAC_FILE`/
`DEPLOYMENT_VIEW` (check-domain-boundary), `FILE_PATH`/`$!` (rebuild-graph) and `SUMMARY_FILE` are all
assigned before the messages that use them. `check-domain-boundary.sh` is a PostToolUse hook, so
"The edit went through — this is a note, not a block" is accurate.

---

## F2 — HIGH — records that passed on 2.7.1 now block, and the CHANGELOG says they do not

Fixture: a 2.7.1-era project mid-release. `workflow.id: release`, one round-1 record, `lens: correctness`,
`verdict: ship`, one HIGH marked `fixed` with a `resolved_by` — the exact shape 2.7.1's template
produced (`verified_by` did not exist as a field).

```
$ python3 ../old/check_review.py --change .hitl/current-change.yaml --reviews .hitl/reviews --root .
Release gate: adversarial review present, fresh, and cleared.
EXIT=0

$ python3 ../new/check_review.py --change .hitl/current-change.yaml --reviews .hitl/reviews --root .
[BLOCK] LENS_FLOOR: round 1 was reviewed through 1 lens (correctness) — a release needs at least 2 distinct ones. ...
[BLOCK] UNVERIFIED_FIX: .hitl/reviews/GH-100-round1.yaml: findings[0] is a HIGH marked fixed with no verified_by ...
EXIT=2
```

The more common shape is worse, because it blocks even a project that did everything the skill asked.
Round 1 with two lenses (the documented practice), round 2 as the single-reviewer verification pass:

```
$ ls .hitl/reviews/   # r1a=correctness, r1b=consequence, r2=correctness
$ python3 ../new/check_review.py ...
[BLOCK] LENS_FLOOR: round 2 was reviewed through 1 lens (correctness) — a release needs at least 2 distinct ones. ...
EXIT=2
```

Only the top round is counted, so a re-review after fixes now has to be two reviewers as well. Nothing
in the diff says that; `ai/shared/adversarial-review.md` presents the floor as a property of "a round"
without distinguishing a first round from a verification round.

Against that, `CHANGELOG.md`:

- line ~37: *"warns elsewhere so existing records keep validating"*
- line ~103, **Note for existing projects**: *"Records written before this release keep validating: ...
  and `verified_by` is only enforced at release."*

Both are false in the only place the gate is a required step. "Enforced at release" and "existing
records keep validating" cannot both be true of a release gate. `LENS_FLOOR` is not mentioned in the
upgrade note at all, and it is the block an upgrader hits first.

**Fix:** either say so honestly in the note ("a release in progress on 2.7.1 will need a second lens
and `verified_by` on any closed CRITICAL/HIGH before it will pass"), or scope both new rules to records
whose `schema_version` postdates the change.

---

## F3 — HIGH — the escape `LENS_FLOOR` names throws the review away

The block message says: *"...or record the decision to ship without one as an acknowledged skip."*
The only acknowledged skip the validator honours is `_acknowledged_skip()`, keyed on
`step: adversarial_review` — which returns **before** any record is read. There is no per-lens waiver.

Applied to the three genuine records from F2:

```
$ cat >> .hitl/current-change.yaml <<'EOF'
skips:
- step: adversarial_review
  ack_by: prasad
  reason: "round 2 was a single-lens verification pass"
EOF
$ python3 ../new/check_review.py ...
[warn] REVIEW_WAIVED: GH-100 is shipping WITHOUT an adversarial review.
        Acknowledged by prasad: round 2 was a single-lens verification pass
        Recorded in the change file, and it stays there.
Release gate: PASSED ON A WAIVER — no adversarial review was honoured.
EXIT=0
```

Three completed rounds, and the durable record now says none happened — permanently, because the
waiver "stays there". The gate's own docstring calls the waiver the honest escape that stops the gate
being deleted at 2am; pointing a lens-count complaint at it converts a bookkeeping shortfall into a
false governance record. That is a worse outcome than the block.

**Fix:** either add a `step: adversarial_review_lens_floor` skip that waives only the count, or drop
the sentence and tell people to run the second lens.

---

## F4 — HIGH — the new release rules are switched off for this release

`is_release` is `str(change["workflow"]["id"]).lower() == "release"`. At HEAD:

```
$ python3 -c "import yaml;d=yaml.safe_load(open('.hitl/current-change.yaml'));print(d['change_id'],d['status'],d['workflow']['id'])"
GH-88-adversarial-review-loop planning development
```

HEAD is `chore(release): 2.8.0 — release notes, version bump, regenerated catalog`, whose message says
"Steps 1-4 of the release workflow". The release workflow is being run; the change file was never
switched to it. So for this release, `LENS_FLOOR` never fires and `UNVERIFIED_FIX` degrades to a warning.
Using HEAD's real change file, one lens, one CRITICAL closed with a fabricated commit and no evidence:

```
$ python3 ci/adversarial/check_review.py --change $S/change.yaml --reviews $S/reviews --root .
[warn] UNVERIFIED_FIX: .../r1.yaml: findings[0] is a CRITICAL marked fixed with no verified_by ...
Release gate: adversarial review present, fresh, and cleared.
EXIT=0
```

The same records with `workflow.id: release`:

```
[BLOCK] LENS_FLOOR: round 1 was reviewed through 1 lens (upgrade) — a release needs at least 2 distinct ones. ...
[BLOCK] UNVERIFIED_FIX: ... findings[0] is a CRITICAL marked fixed with no verified_by ...
EXIT=2
```

Two of the four fixes this release is named for are unexercised by the release that ships them, and the
gate prints the reassuring line while it happens. Nothing checks that a release commit is governed by a
release change file — `_claimed_without_record` looks at `adv_*` step keys, which the development
workflow also has.

Related, same root: at HEAD the repo's own gate is red.

```
$ python3 ci/adversarial/check_review.py
[BLOCK] REVIEW_MISSING: no review record for GH-88-adversarial-review-loop in .hitl/reviews/
EXIT=2
```

That one is expected mid-release (this review is step 5). The defect is that when the record does land,
it will land against a `development` change and the release-only rules will stay dark.

**Fix:** switch `.hitl/current-change.yaml` to the release change before the review round, or key
`is_release` off something the release path cannot forget — the presence of a version bump in the diff,
or `--release` passed by `dev-validate` during the release workflow.

---

## F5 — HIGH — the skill tells you both to name the reviewers and not to

`ai/claude/adversarial-review/SKILL.md`:

```
$ grep -n -i "name" ai/claude/adversarial-review/SKILL.md | sed -n '3,5p'
92:reviewers filed under one; a hand-invented name defeats it silently.
94:**Do not give the reviewers names.** A named agent becomes an addressable peer rather than a task
140:Give each reviewer a distinct name so the reports are attributable.
```

Line 140 is a leftover from 2.7.1 and is the **last line of Step 3** — the sentence sitting closest to
where the reader spawns the agents. Line 94 is buried mid-step. Per the CHANGELOG this exact instruction
is why ten reviewers produced 13k–25k-character reports and "not one was delivered ... recovered by hand
out of log files". The release ships the fix and the cause in the same step.

The wiring test that guards this checks only that the new sentence exists:

```
ci/wiring/test_wiring.py:353  assert ".hitl/reviews/incoming/" in body
ci/wiring/test_wiring.py:355  assert re.search(r"(?i)do not give the reviewers names|...", body)
```

Nothing asserts the contradicting sentence is gone. All 762 tests pass with it in place.

**Fix:** delete line 140. That is the whole fix.

---

## F6 — MEDIUM — the lens floor counts strings, not lenses

`UNKNOWN_LENS` is deliberately a warning, so `LENS_FLOOR`'s `distinct` set can contain anything.

```
### two invented lenses satisfy the release floor        (a.yaml lens: banana, b.yaml lens: kumquat)
[warn] UNKNOWN_LENS: a.yaml uses lens 'banana' ... It still counts ...
[warn] UNKNOWN_LENS: b.yaml uses lens 'kumquat' ... It still counts ...
Release gate: adversarial review present, fresh, and cleared.
EXIT=0
```

Worse, a lens that canonicalises to the **empty string** counts as a distinct lens, because the filter
tests the raw value for truthiness and the set stores the canonical one:

```
### lens: correctness  +  lens: second        (canonical_lens("second") == "")
[warn] UNKNOWN_LENS: b.yaml uses lens 'second' ...
Release gate: adversarial review present, fresh, and cleared.
EXIT=0
```

`second`, `two`, `bis`, `b` and any all-digit value all canonicalise to `""`. So the "second distinct
lens" the floor demands can literally be nothing — and `second` is the most natural thing to type for a
second reviewer, which is the very habit the DUPLICATE_ROUND message was rewritten to discourage. It
also collides with a record that has no `lens:` at all, which reports as duplicate lens `'(unset)'`.

**Fix:** drop empty canonical results from `distinct`, at minimum. Counting only catalog ids toward the
floor would be stronger, but that trades against the deliberate decision to keep unknown lenses valid.

---

## F7 — MEDIUM — `canonical_lens()` strips a bare `b` and bare digits

`re.sub(r"[\s_-]*\d+$", ...)` and `re.sub(r"[\s_-]*(bis|b|two|second)$", ...)` both make the separator
optional, so they eat word-final characters rather than only disambiguating suffixes.

```
  'costb'              -> 'cost'         in_catalog=True    <- wrong bucket, silently
  'job'                -> 'jo'           in_catalog=False
  'web'                -> 'we'           in_catalog=False
  'climb'              -> 'clim'         in_catalog=False
  'ipv4'               -> 'ipv'          in_catalog=False   } collapse into one lens
  'ipv6'               -> 'ipv'          in_catalog=False   }
  'api-v1'             -> 'api-v'        in_catalog=False   } collapse into one lens
  'api-v2'             -> 'api-v'        in_catalog=False   }
  'oauth2'             -> 'oauth'        in_catalog=False
  'tier1'/'tier2'      -> 'tier'                            } collapse into one lens
```

All 13 catalog ids round-trip unchanged, so the shipped vocabulary is safe. The exposure is entirely on
user-chosen names, where the failure is silent: two genuinely different reviewers (`ipv4` and `ipv6`,
`api-v1` and `api-v2`) are reported as a `DUPLICATE_ROUND` block and count as one toward the floor,
and the message tells them the cause is numbering a duplicate — which is not what they did.

**Fix:** require the separator: `[\s_-]+\d+$` and `[\s_-]+(bis|b|two|second)$`. That still catches
`consequence-2`, `consequence_2` and `consequence 2`, which is the whole stated purpose.

---

## F8 — MEDIUM — an undocumented fifth alias, into the wrong phase

`LENS_ALIASES` has five entries. `ai/shared/adversarial-review.md` § "Older names" documents four
(`destructiveness`, `migration`, `install`, `perf`); the CHANGELOG documents the same four.
`functionality` → `fitness` appears nowhere but the code.

It is also the wrong bucket. `fitness` is the **design**-phase lens ("Does this design satisfy the
requirement it claims to?"); the code-phase lens is `correctness`. "Functionality" names a question
about behaviour, not about design-to-requirement fit. A pre-catalog project with a `functionality`
reviewer and a `fitness` reviewer in one round now gets two blocks and no way to see why:

```
### lens: functionality  +  lens: fitness
[BLOCK] DUPLICATE_ROUND: round 1 has more than one record for lens 'fitness' (a.yaml, b.yaml) ...
[BLOCK] LENS_FLOOR: round 1 was reviewed through 1 lens (fitness) — a release needs at least 2 distinct ones ...
EXIT=2
```

Neither record says `fitness`. The mirror test is one-directional — it asserts every alias promised by
the catalog is in the code, never that every alias in the code is in the catalog:

```
ci/wiring/test_wiring.py:339  unmapped = sorted(a for a in aliases if a not in check_review.LENS_ALIASES)
```

So the code comment "A test asserts these ids match the catalog" is true of `LENSES` (both directions)
and false of `LENS_ALIASES`.

**Fix:** map `functionality` → `correctness`, document it in § Older names, and add the reverse
assertion to the wiring test.

---

## F9 — MEDIUM — the portal announces v2.7.1 in the commit that publishes 2.8.0

```
$ grep -rn "v2\.7\.1" site/*.html
site/compare.html:130:      <h3>2.x — v2.7.1 <span class="pill live">CURRENT · hitl@hitl</span></h3>
site/architecture.html:283:  <footer>HITL v2.7.1 (current 2.x line) · counts reflect the shipped release</footer>
site/index.html:263:  <footer>HITL · current release: v2.7.1 (<code>hitl@hitl</code>) ...
site/going-ai-native.html:678:  <footer>HITL v2.7.1 (current 2.x line) · the workflow, gates, and registers ... are shipped and enforced, not roadmap</footer>
```

`ai/claude/plugin/plugin.json` says `2.8.0` in the same commit. The site work in this release moved the
footers from v2.1.1 to v2.7.1 — the previous release, not the one being cut — and the new "What's new"
grid on `index.html` stops at a `2.7` pill. This is the first thing a fresh installer reads, and the
2.8.0 changelog entry names exactly this ("The portal had not moved since v2.1.1 ... it advertised none
of ...") as a defect it fixed. It is re-broken by one version in the act of fixing it, and no test
compares `plugin.json` to the site. The `going-ai-native.html` footer's "shipped and enforced, not
roadmap" claim now sits under a stale version number, which is the worst place for it.

The catalog counts on `index.html` ("All 8 workflows, ... 96 steps and 3 substeps") are correct —
verified against `ai/shared/workflows.yaml`: 8 workflows, 99 total rows, 3 with a non-numeric `n`.

**Fix:** a wiring assertion that the version in `site/*.html` equals `plugin.json`'s, and bump the four.

---

## F10 — MEDIUM — "plain text, no icons" cannot turn off the icons

`ai/claude/preferences/SKILL.md:373` states, unqualified: *"HITL marks state with a small set of icons
by default — 🔒 paused, 🧭 where you are, ⚠️ irreversible, ✅ done. **"Plain text" turns them off.**"*
The CHANGELOG repeats it. The 42 rewritten messages this release is built around are `echo` statements
in bash; no hook reads any preference:

```
$ grep -rn "PREFS\|prefer\|icon\|plain.text" ai/claude/hooks/*.sh
ai/claude/hooks/_steps.sh:226:# Rules: prefer an explicit `expected_branch`; ...    <- unrelated
```

With an ACTIVE prefs block in `CLAUDE.md` carrying "plain text, no icons":

```
$ echo '{"tool_name":"Edit","tool_input":{"file_path":"src.py"}}' | CLAUDE_PROJECT_DIR="$T" bash hooks/check-hitl-context.sh
🧭 You are on 'other-branch', but the tracked change GH-7 lives on 'issue/42-something'.
...
```

The preference governs model prose only. Saying it "turns them off" while the newly-iconified surface
ignores it is a promise the release cannot keep, and the person most likely to set it is the person
already irritated by the glyphs.

**Fix:** scope the sentence to what HITL writes, or have the hooks honour `HITL_NO_ICONS`.

---

## F11 — LOW — the icon vocabulary is larger than the vocabulary that is documented

CHANGELOG line 96 and `preferences/SKILL.md` both enumerate four glyphs. Enumerating what is actually
in the hooks:

```
🔒 U+1F512 x4    🧭 U+1F9ED x3    ⚠ U+26A0 x4    ✅ U+2705 x1    🔄 U+1F504 x1    📝 U+1F4DD x1
```

`🔄` (rebuild-graph.sh) and `📝` (write-session-summary.sh) are both new in this release and outside the
documented set. Neither marks state in the sense the doc defines ("🔒 paused, 🧭 where you are,
⚠️ irreversible, ✅ done"); both decorate a status line, which is the thing the rationale rules out.

## F12 — LOW — "say it last" is item 7 of 8

`SKILL.md:124-129`. Item 7 is *"Where the report goes ... Say it last so it is the instruction nearest
the end of the brief"*, and item 8 (working rules) follows it. The stated reason for the ordering is
defeated by the ordering. Two lines apart.

---

## Areas checked and sound

- **Hook control flow.** No exit code, branch, or variable-reference change across the five hooks other
  than F1; every non-`echo`, non-comment line is identical to v2.7.1 (one list-indent excepted) and
  `bash -n` passes on all five. All variables interpolated in the new messages are assigned before use,
  except `EXPECTED` on the path in F1.
- **`.hitl/reviews/incoming/`.** Not gitignored (`git check-ignore` exits 1; `.gitignore` scopes its
  `.hitl/` rules to `*.tmp`, `*.migrated`, `first-pass-choices.json`, `backups/`). No retirement,
  cleanup, or onboarding step touches it — the only references in the tree are the skill and one wiring
  test. No collision with the gate: `os.listdir(reviews_dir)` skips `incoming` because it does not end
  in `.yaml`, and the same `.yaml` filter guards `_claimed_without_record` and `_adverse_verdict`.
  Untracked reports do not trip `UNCOMMITTED_CHANGES` or stale a review, because `_dirty()` and
  `_is_fresh()` both exempt the `.hitl/` prefix.
- **Reading findings from every record in the top round.** The rewrite is correct and does what it
  claims; a second reviewer's open CRITICAL is now seen. It does widen `UNSIGNED_ACCEPTANCE` and
  `REVIEW_MALFORMED` to every record in the round, which is a behaviour change for upgraders in the
  same family as F2, but I could not construct a case where the widening is wrong.
- **Catalog vocabulary.** All 13 catalog ids round-trip through `canonical_lens()` unchanged.
- **Version/plugin manifest.** `plugin.json` is `2.8.0` and matches the CHANGELOG heading.
- **Test suite.** 762 pass. None of F1–F12 is caught by one.

---

## Verdict

**DO NOT SHIP.**

Smallest change that clears the blocking set:

1. **F1** — `ai/claude/hooks/check-hitl-context.sh:151,154`: `${EXPECTED:-…}` or an `[[ -n "$EXPECTED" ]]`
   branch. One file, two lines. This is a user-facing hard block that currently gives no usable remedy.
2. **F5** — delete `ai/claude/adversarial-review/SKILL.md:140`. One line, and it removes the instruction
   that caused the failure this release exists to fix.
3. **F4** — put the release on a `workflow.id: release` change file before the review round, so the two
   new rules apply to the release that introduces them. Otherwise they ship untested in production use.
4. **F3** — remove "or record the decision to ship without one as an acknowledged skip" from the
   `LENS_FLOOR` message, or implement a lens-only waiver. As written it instructs people into a false
   governance record.
5. **F2** — rewrite the CHANGELOG's "Note for existing projects" to say what actually happens to a
   release in progress on 2.7.1. Documentation-only, but it is the sentence an upgrader acts on.

F6–F8 are cheap and worth taking in the same pass (`distinct` should drop empty canonical results;
require the separator in both `canonical_lens` regexes; remap and document `functionality`). F9–F12 are
not release blockers on their own.
