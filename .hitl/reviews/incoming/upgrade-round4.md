# Adversarial review — round 4, upgrade lens

**State under review:** `1d4b2fd` on `main` (2.8.0 release candidate)
**Scope:** `git diff v2.7.1..HEAD` (the whole release), with particular attention to `git diff ff879f3..HEAD` (the scope reduction)
**Stance:** refute. Every finding below was reproduced; commands and observed output are inline.
**Verdict:** DO NOT SHIP

The two cut checks (`LENS_FLOOR`, `UNVERIFIED_FIX`) are gone from the tree and I did not re-litigate
them. I confirmed the removal is clean at the code level: no dangling references to
`RELEASE_LENS_FLOOR`, `_looks_like_a_release`, `is_release`, `wf_id` or `UNVERIFIED_FIX` survive
anywhere under `ci/`, `ai/`, `tools/`, `.github/` or `site/`, and the full suite is green
(`python3 -m pytest ci -q` → `721 passed`). The problems below are in what *did* ship.

---

## Reproduction environment

All fixtures were built in `mktemp -d` scratch directories. Two copies of the validator were staged
for A/B comparison:

```bash
W=$(mktemp -d)
git show v2.7.1:ci/adversarial/check_review.py > $W/old/check_review.py
cp ci/adversarial/check_review.py                 $W/new/check_review.py
```

and two copies of the hooks, likewise `hooks-old/` (v2.7.1) vs `hooks-new/` (HEAD).

---

## CRITICAL-1 — a reused finding id silently closes an open CRITICAL from an earlier round

The one thing that shipped from the cut work is the carry-forward: "an open CRITICAL or HIGH now
survives every round until something resolves it." It does not survive the most ordinary thing a
second round does.

`check_review.py` builds `_resolved` from *every* record in *every* round, keyed on `(id, claim)`,
and closes an earlier-round finding if **either** key matches:

```python
_resolved.add(_k)                       # for _k in _identity(_item), any round, any severity
...
and not any(k and k in _resolved for k in _identity(_item))
```

Finding ids restart at `F1` in each round — the same file says so 40 lines above, in the
`RECURRING_FINDING` comment: *"Compared on the claim, because ids restart per round."* So a round-2
`F1` marked `fixed` closes a round-1 `F1` that has nothing to do with it.

```
Round 1: F1  CRITICAL  "the upgrade deletes the users table"   status: open
Round 2: F1  LOW       "a typo in the help text"               status: fixed
```

Observed (`python3 $W/repro2.py`):

```
=== id_collision_resolves_unrelated_critical ===
  old  blocks=NONE
  new  blocks=NONE
=== control_distinct_ids ===          # identical, except round 2 uses id F9
  old  blocks=NONE
  new  blocks=['FINDING_OPEN']
        [BLOCK] FINDING_OPEN: CRITICAL: the upgrade deletes the users table — fix it, or accept it explicitly with accepted_by
```

Changing one character of an unrelated LOW's id is the difference between the release blocking and
the release passing with an open CRITICAL. This is squarely on the designed path, because Step 5 of
the skill *creates* carried-over open findings by design: *"A finding they have not answered is
`open`."*

Round 3 found this independently (`.hitl/reviews/incoming/consequence-round3.md` CRITICAL-1,
`bypass-round3.md` B3-1). It is **not** part of either cut check — `git log -S"_resolved"` shows it
was introduced by `ff879f3` and untouched by `1d4b2fd` — so the scope reduction did not remove it.
It ships.

**Smallest fix:** require both keys to match (`fid and claim` both present and both equal), or scope
the resolved-set by round so a later round can only close what it names by claim.

---

## CRITICAL-2 — an earlier-round finding with a typo'd status or severity is dropped silently

The carry-forward collector filters earlier rounds on exact string membership and never validates
them. A malformed field in the **top** round is a `REVIEW_MALFORMED` block; the identical malformed
field in an **earlier** round is silence — no block, no warning, finding gone.

Observed (`python3 $W/repro4.py`):

```
=== earlier_round_bad_status_silently_dropped ===     # round 1: CRITICAL, status: "unresolved"
  blocks=NONE
  warns =NONE
=== top_round_bad_status_is_flagged ===               # same record, now the top round
  blocks=['REVIEW_MALFORMED']
=== earlier_round_bad_severity_dropped ===            # round 1: severity: "CRIT", status: open
  blocks=NONE
  warns =NONE
```

The gate is fail-closed everywhere else; here a one-word slip fails it open, and it fails open
*quietly*, which is worse than the pre-2.8.0 behaviour where earlier rounds were ignored openly.
Also found by round 3 (`consequence-round3.md` CRITICAL-2). Ships.

**Smallest fix:** run the same severity/status validation over earlier-round findings, and block on
a malformed one rather than skipping it.

---

## HIGH-1 — "Nothing that validated before this release fails now" is false, and was already found false once

`CHANGELOG.md`, "Note for existing projects":

> Run `/hitl:dev-update`. **Nothing that validated before this release fails now.**

Three record sets that pass on v2.7.1 and block on HEAD (`python3 $W/repro.py`, `$W/repro3.py`):

| fixture | v2.7.1 | HEAD |
|---|---|---|
| r1 open CRITICAL, r2 clean and silent about it | `blocks=NONE` | `blocks=['FINDING_OPEN']` |
| two reviewers in r1, the CRITICAL in the alphabetically-first file | `blocks=NONE` | `blocks=['FINDING_OPEN']` |
| r1 filed as `consequence` + `consequence-2` | `blocks=NONE` | `blocks=['DUPLICATE_ROUND']` |

The last one matters more than it looks. v2.7.1's `DUPLICATE_ROUND` message told people *"give each a
distinct `lens:`"*, and `consequence-2` is the obvious way to comply. `canonical_lens()` now folds it
back and blocks it.

This is not a new discovery: round 1 recorded it as `C2-H1` — *"The CHANGELOG told existing projects
the upgrade is validation-neutral. Records that passed on 2.7.1 now block at release."* — and
`54abacb` fixed it by naming the two new rules explicitly. `1d4b2fd` reverted that note along with
the cut checks and restored the refuted sentence, in a stronger form (bolded). The two mechanisms
that make it false both still ship.

Worse: `C2-H1` is still recorded `status: fixed` in
`.hitl/reviews/GH-92-release-2.8.0-round1-consequence.yaml`, with

> `verified_by:` CHANGELOG 'Note for existing projects' now states exactly which two rules are new…

That note no longer exists. This release is about false closures, and it is shipping one about
itself.

**Smallest fix:** replace the sentence with what is actually true — an open CRITICAL/HIGH from any
earlier round now blocks, and a second reviewer filed as `<lens>-2` now blocks — and reopen `C2-H1`.

---

## HIGH-2 — the shipped record template still tells users earlier rounds are history

`ai/shared/templates/adversarial-review-record.yaml:12`, unchanged by this release:

```yaml
round: 1                     # highest round decides; earlier rounds are history
```

The gate no longer behaves that way, and the template is the file every reviewer copies. Nothing in
`ai/claude/adversarial-review/SKILL.md` or `ai/shared/adversarial-review.md` documents the
carry-forward either:

```bash
$ grep -rn "highest round decides\|earlier rounds are history" \
    ai/shared/templates/adversarial-review-record.yaml ai/claude/adversarial-review/SKILL.md \
    ai/shared/adversarial-review.md CHANGELOG.md
ai/shared/templates/adversarial-review-record.yaml:12:round: 1  # highest round decides; earlier rounds are history
```

Only the CHANGELOG mentions it. A user on 2.8.0 whose release blocks on a round-1 finding will read
the template and conclude the gate is broken.

**Smallest fix:** one line in the template.

---

## HIGH-3 — "a dropped lens is a skip, recorded like any other" has no valid representation, and following it fails the PR build

New in this release, in both shipped files:

- `ai/claude/adversarial-review/SKILL.md:73` — *"**A dropped lens is a skip.** Record it like any other…"*
- `ai/shared/adversarial-review.md` — *"**A lens they drop is a skip**, recorded like any other…"*

Step 2 actively invites the drop (*"Swap or drop any of them"*). But `ai/shared/skip-record.md`
defines `step` as *"the lightened workflow-step `key`"*, and a lens is not a step. Recording it as
instructed:

```bash
# change file with a complete development plan + one skip: step: adv_code_lens_security
$ python3 ci/first-pass/check_skips.py $d/.hitl/current-change.yaml
[warn] FP_ABSENT_ENFORCED: first_pass is absent, but this change carries attributed skips — enforcing the full ruleset on them.
[warn] LEDGER_STEPS: skip record references unknown step 'adv_code_lens_security'
[BLOCK] UNKNOWN_STEP: skip references step 'adv_code_lens_security' not in the workflow catalog (criticality unresolvable)
exit=2
```

`UNKNOWN_STEP` is in `NON_WAIVABLE`. `.github/workflows/first-pass-check.yml` — which onboarding
installs into every product repo — runs this on **every** pull request. So a user who accepts the
new lens plan, drops one lens, and lets the agent record it as the skill instructs gets a red,
non-waivable PR check. An attributed skip also drops the change through the `first_pass`-absent
early return into the full ruleset, so this fires on ordinary non-First-Pass changes.

**Smallest fix:** say where a dropped lens is recorded — the review record's own fields, or the
skip against the `adv_design`/`adv_code` step with the lens named in `reason` — and stop calling it
"a skip like any other".

---

## MEDIUM-1 — the icon preference the release advertises does not exist

`ai/claude/preferences/SKILL.md` (shipped, new in this release):

> HITL marks state with a small set of icons by default — 🔒 paused, 🧭 where you are, ⚠️ irreversible,
> ✅ done. *"Plain text"* turns them off.

and the CHANGELOG repeats it. It does not turn them off. The icons are literal bytes in five shell
scripts that read no configuration:

```bash
$ grep -l "CLAUDE.md\|PREFS\|preferences" ai/claude/hooks/*.sh
NONE
```

Reproduced with a project whose `CLAUDE.md` carries an ACTIVE PREFS block reading
`**Style:** plain text, no icons`:

```
🔒 The design for this change is not approved yet, so code edits are on hold.
...
exit=2
```

The rest of the sentence — *"and cannot turn off what an icon marks"* — is sound and worth keeping.
The first half is a promise nothing implements.

**Smallest fix:** delete the claim, or scope it to what preferences actually shape (the assistant's
own prose, not hook output).

---

## MEDIUM-2 — six icons ship against a four-icon vocabulary, and the fourth has no live instance

Declared set, in both the CHANGELOG and `preferences/SKILL.md`: 🔒 paused, 🧭 where you are,
⚠️ irreversible, ✅ done — *"extending the existing vocabulary rather than decorating."*

Actually shipped:

```bash
$ grep -n "🔒\|🧭\|⚠️\|✅\|🔄\|📝" ai/claude/hooks/*.sh
ai/claude/hooks/rebuild-graph.sh:57:        🔄 Updating the knowledge graph …
ai/claude/hooks/write-session-summary.sh:76:  📝 Session summary saved: …
```

🔄 and 📝 are undeclared, and both mark an ordinary informational notice — decoration, by the
release's own definition.

⚠️ has the opposite problem. Its only new use is the domain-boundary parse-error message, and that
message is unreachable: `set -euo pipefail` kills the script when the command substitution on line 58
fails, so the `PYEXIT` check on line 87 is never reached.

```
### 13 boundary-malformed [old] exit=1
  |HITL_PARSE_ERROR: while parsing a flow sequence …
### 13 boundary-malformed [new] exit=1
  |HITL_PARSE_ERROR: while parsing a flow sequence …
```

The unreachability is pre-existing (identical in v2.7.1) — but this release wrote a new user-facing
message onto a dead path and counted it among "all 46". The published ⚠️ = irreversible mapping has
zero true instances in the rewritten hooks.

---

## MEDIUM-3 — the portal ships contradicting itself about which version is current

The release's stated fix is *"The portal had not moved since v2.1.1."* At `1d4b2fd`:

```bash
$ grep -n "2\.7\.1\|2\.8\.0" site/*.html
site/index.html:263:          current release: v2.7.1 (hitl@hitl) …
site/architecture.html:283:   HITL v2.7.1 (current 2.x line) …
site/compare.html:130:        2.x — v2.7.1  CURRENT · hitl@hitl
site/going-ai-native.html:678: HITL v2.7.1 (current 2.x line) …
site/catalog.html:299:        HITL v2.8.0 (2.x line) · generated from tools/workflow-catalog/catalog.yaml
```

The generated page tracks the version; the four hand-maintained pages do not. On deploy the portal
will say 2.7.1 is current on the home page and 2.8.0 on the catalog page — the same drift class the
release claims to have closed, one version later.

---

## LOW — reproduced, lower consequence

- **`.hitl/reviews/incoming/` is ignored here but not in onboarded projects.** `.gitignore` gained
  the entry for this repo; `bash tools/scripts/init-project.sh $T --tool claude` emits a
  `.gitignore` with only `docs/session-logs/`, `.hitl/people/` and Python bytecode. Every onboarded
  project will accumulate untracked 13k–25k-char reports under `.hitl/`. *(Already accepted at
  MEDIUM by `pappar` as part of `C2-M`; noted, not re-litigated.)*

- **`UNKNOWN_LENS` and `DUPLICATE_ROUND` point at a file that is not in a product repo.** Both new
  messages say *"the catalog in shared/adversarial-review.md"*. Onboarding copies only
  `ci/adversarial/*.py`; `find $T -path "*shared*" -name "*.md"` on a fresh project returns nothing.
  The catalog exists only inside the plugin.

- **Empty-variable interpolation is still live on two paths, both unchanged from v2.7.1.**
  `CURRENT_BRANCH` is empty on a detached HEAD (mid-bisect, tag checkout) → `🧭 You are on '', but
  the tracked change GH-1 lives on 'main'.` `CHANGE_ID` is empty when `change_id:` has no value →
  `✅  looks finished …` and `🧭 Heads up: src/app.py sits outside what  said it would touch.` The
  round-1 fix guarded `EXPECTED` and left these; v2.7.1 degrades identically, so neither is a
  regression. *(Already recorded open as part of `R2C-4`.)*

- **The skill contradicts itself across Steps 4 and 5.** Step 4 (unchanged): *"Reproduces, but is by
  design → it is `accepted`, not `open`, and needs a name against it."* Step 5 (new): *"Never accept
  on someone's behalf, and never write a name into `accepted_by` that did not say the words."* The
  only consistent reading is that Step 4 defers the name to Step 5, which it does not say — and an
  agent following Step 4 literally writes `accepted` with no name and trips `UNSIGNED_ACCEPTANCE`.

---

## Areas I attacked and could not break

- **Hook exit codes and control flow are identical to v2.7.1 on every path I could reach.** 14
  hand-built cases across `check-hitl-context.sh` and `check-domain-boundary.sh` (no active change,
  missing required field, mismatch with and without `expected_branch`, branch gone, status gate,
  docs-vs-source, approved, empty `change_id`, empty `status`, outside `allowed_paths`, malformed
  YAML, IaC edit) — every one produced the same exit code old and new. Corroborated by running the
  *current* test suites against the *v2.7.1* scripts: `test_check_platform_ready.py` 59/60 pass
  (the one failure is a relocated-fixture path error, not behaviour) and
  `test_check_hitl_context.py` 13/14 (the one failure is the deliberately relaxed wording
  assertion). Message text changed; nothing else did.

- **`check-platform-ready.sh` fails closed on every path tested** — unparseable register, empty
  register, missing PyYAML branch guarded by a numeric `TIER`. `${TIER}` cannot be empty
  (`[[ "$TIER" =~ ^[0-9]+$ ]] || TIER=2` precedes every use).

- **`rebuild-graph.sh` and `write-session-summary.sh`** guard their interpolated variables and are
  message-only changes.

- **The catalog-page generator does what the release says.** Removing the `release` entry from
  `ORDER` and re-running exits 1 with `ORDER does not cover the catalog`; the committed
  `site/catalog.html` is byte-identical to fresh generator output; the restored nav links are
  present.

- **The lens catalog and the gate agree.** 13 ids in `LENSES`, 13 in the catalog tables, aliases all
  mapped; the wiring guard that asserts this passes.

- **Fresh onboarding delivers what the skill needs.** `init-project.sh` produces
  `.claude/commands/adversarial-review.md` and `ci/adversarial/check_review.py`; the plugin's
  `shared/adversarial-review.md` and `shared/ci/adversarial/` exist at the plugin root, so the
  skill's plugin-relative references resolve.

- **Hook wrappers are version-agnostic.** `.hitl/hooks/*.sh` discover the plugin path from
  `installed_plugins.json` at run time, so an upgrade needs no re-wiring.

- **The scope reduction left no dead code.** No shipped file references the removed identifiers.

---

## One more thing the gate itself says

```bash
$ python3 ci/adversarial/check_review.py
[BLOCK] REVIEW_STALE: …round2-bypass.yaml reviewed 54abacb2eabd but 1d4b2fd439fe is about to ship
[BLOCK] FINDING_OPEN: ×7 (3 CRITICAL, 4 HIGH)
[BLOCK] VERDICT_NOT_SHIP: …
Release gate: BLOCKED.
exit=2
```

The release cannot pass its own gate at `1d4b2fd`. Round 3's findings were never written to a
record at all (only rounds 1 and 2 exist under `.hitl/reviews/`), so two of round 3's CRITICALs —
the two I reproduced above — have no record and no disposition.

---

## Verdict

**DO NOT SHIP.**

The scope reduction was the right call and it is clean at the code level, but it is not a clean
round. Four defects reproduce in what remains, and two of them are in the single feature the
CHANGELOG holds up as having survived three rounds of review.

**The smallest change that would fix it**, in order:

1. `_identity` must require both id *and* claim to match before closing an earlier-round finding,
   and earlier-round findings must be schema-validated rather than skipped. (CRITICAL-1, CRITICAL-2
   — roughly ten lines in `check_review.py`.)
2. Replace the "Nothing that validated before this release fails now" sentence with the two things
   that do now block, and reopen `C2-H1`. (HIGH-1 — three lines of prose.)
3. One line in the record template: earlier rounds are not history. (HIGH-2.)
4. Say where a dropped lens is actually recorded, or drop the sentence. (HIGH-3 — two lines across
   two files.)
5. Delete the "*Plain text* turns them off" claim, declare 🔄 and 📝 or remove them, and bring the
   four hand-maintained portal footers to 2.8.0. (MEDIUM-1..3.)

Then run one round against the resulting sha — `upgrade` plus one other lens — and record it.
