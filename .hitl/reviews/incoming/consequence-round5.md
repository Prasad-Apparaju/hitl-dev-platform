# Consequence — round 5 (confirming review)

**State under review:** `0b6c5f7507c75594328e2bae13a39c94a5a86f84` on `main`
**Lens:** consequence — what this destroys, exposes, or makes unrecoverable
**Stance:** refute
**Scope:** `diff v2.7.1..HEAD` (everything that ships), `diff 1d4b2fd..HEAD` (the last removals + doc fixes)

Note on the working tree: `git status` was clean when this review started and is now dirty
(`CHANGELOG.md`, `ai/shared/adversarial-review.md`, `ci/adversarial/check_review.py`,
`ci/adversarial/test_check_review.py`). Those are not mine. Every fixture below was built from
`git show HEAD:<path>` and `git show v2.7.1:<path>`, so this review is of the committed state of
`0b6c5f7`, not of the working tree.

**Verdict: DO NOT SHIP.** The code is sound. The CHANGELOG is not — it repeats, at a higher
count, the same class of false claim the entry itself says it corrected. The fix is documentation
only; no code change is required.

---

## 1. "Nothing that validated before this release fails now" — verified myself

Method: both validators loaded side by side and run over identical fixtures.

```
git show v2.7.1:ci/adversarial/check_review.py > $D/check_old.py
git show HEAD:ci/adversarial/check_review.py   > $D/check_new.py
```

- **47 hand-built record shapes** (`harness.py`), each a throwaway git repo with one commit and
  review records naming it: clean rounds, open/fixed/accepted findings at every severity, two and
  three reviewers per round, alias lenses, numbered lenses, missing lenses, non-mapping findings,
  malformed severities and statuses, stale shas, waivers, unreadable foreign records, round 3+,
  recurring claims, non-int rounds.
- **6000 randomised shapes** (`fuzz2.py`, seed 20260820, 1–4 records per case, git calls stubbed
  deterministically so `_is_fresh` / `_dirty` are held constant across both versions).

### Result — the dangerous direction is clean

```
cases 6000 secs 66.4
FAIL-OPEN REGRESSIONS (a code old emitted that new does not): 0
new-only block codes: Counter({'DUPLICATE_ROUND': 621, 'REVIEW_MALFORMED': 141,
                               'FINDING_OPEN': 68, 'UNSIGNED_ACCEPTANCE': 21})
```

Plus 0 in the 47 hand cases. **Nothing that blocked at v2.7.1 passes at HEAD.** The change is
strictly additive to the block set, in both the dedup path (`canonical_lens` is a function, so it
can merge groups but never split one) and the findings path (`latest` is a superset of `{rec}`,
so the aggregated finding list is a superset of the old one). That is the right direction and it
holds under every shape I could construct.

### FINDING H-1 (HIGH) — the reverse direction is real, and it is not what the note says

`CHANGELOG.md`, "Note for existing projects":

> Nothing else changes. Records with one lens, a finding closed with a bare commit id, **a legacy
> lens name**, or an accepted finding with a name against it all validate exactly as they did on 2.7.1.

A legacy lens name alone does validate identically. A legacy lens name **in the same round as its
modern equivalent** does not. `alias_repro.py` builds a history of exactly the shape v2.7.1's own
documentation produced — the skill at v2.7.1 said *"Correctness and destructiveness"*
(`ai/shared/adversarial-review.md:125`) and *"swap a lens ... `migration` for anything that
rewrites data in place"* (`adversarial-review/SKILL.md:67`), while the v2.7.1 template offered
*"correctness | consequence | bypass"*:

```
$ python3 alias_repro.py
=== v2.7.1 exit=0 ===
Release gate: adversarial review present, fresh, and cleared.
=== HEAD   exit=2 ===
[BLOCK] DUPLICATE_ROUND: round 1 has more than one record for lens 'consequence'
  (GH-1-round1-consequence.yaml, GH-1-round1-destructiveness.yaml).
```

Fixture: round 1 = `consequence` + `destructiveness`, round 2 = `correctness`, all clean, all
verdict `ship`. The same flip occurs for `data`+`migration`, `upgrade`+`install`,
`scalability`+`perf`, `fitness`+`functionality` — every pair in `LENS_ALIASES`, which is the map
whose own comment says it exists to accommodate *"older names that still appear in records written
before the catalog existed."* The map accommodates them one at a time and rejects them in pairs.

**Why this is a consequence finding and not a doc nit.** `DUPLICATE_ROUND` is computed from
`records` — every record for the change — not from `latest`. In the reproduction above, round 2 is
the governing round and is clean; the block comes from **round 1**, which is history. Review
records are kept forever by design. So a mid-flight change whose round 1 used an alias pair is
blocked permanently, and the only way out is to edit a review record that has already been written
— the framework asks you to falsify review history to unblock a release. Recoverable in one edit,
but it is the wrong instruction to hand someone at 2am, and it is the exact move
`ci/adversarial/check_review.py`'s own header says the gate exists to prevent.

`/hitl:dev-update` does deliver this: `ai/claude/update/SKILL.md:273` runs
`cp "$ROOT/shared/ci/adversarial/"*.py ci/adversarial/`, overwriting the product repo's validator.

### FINDING H-2 (MEDIUM) — "Two things newly block" is four things

The note enumerates a numbered lens and an open finding on an unselected record. The fuzz found
four distinct new-only codes. Three more shapes, reproduced in `sibling_repro.py`. In each, two
round-1 reviewers on different lenses both say `ship`; only the **filename sort order** decides
which one v2.7.1 inspected, and the defective one sorts first:

```
=== S1 sibling ACCEPTED-with-no-signer, sorts FIRST ===
   v2.7.1 exit=0  (no block)
   HEAD   exit=2  [BLOCK] UNSIGNED_ACCEPTANCE: ...GH-1-round1-aaa-correctness.yaml
=== S2 sibling BAD SEVERITY string ('Criticl'), sorts FIRST ===
   v2.7.1 exit=0  (no block)
   HEAD   exit=2  [BLOCK] REVIEW_MALFORMED: ...
=== S3 sibling findings is a MAPPING not a list, sorts FIRST ===
   v2.7.1 exit=0  (no block)
   HEAD   exit=2  [BLOCK] REVIEW_MALFORMED: ...
```

These are all correct new behaviour — reading every record in the round is the fix, and this is
what the fix looks like. But the note tells an upgrading team to expect two codes and they can get
four. S1 sits directly beside the sentence *"an accepted finding with a name against it ...
validate[s] exactly as they did"*, which invites the reading that acceptance handling is unchanged.

Two smaller collision sources, reproduced but not worth disclosing individually: a lens ending in a
stripped token (`datab` → `data`) and two purely numeric lenses (`2` and `3`, both → `""`) also
collide. Contrived; noted only because they come from the same regex.

---

## 2. The five hook scripts — SOUND

No un-gating on any reachable path. Three independent checks, all clean:

**Structural.** Diffing each hook with every message-emitting line removed leaves exactly one
non-message change across all five files: two `if [[ -n "$EXPECTED" ]]` guards in
`check-hitl-context.sh` that select which sentence prints. Both sit inside the branch-mismatch arm;
the arm's `exit 2` is outside them. `EXPECTED` is assigned unconditionally at line 141 before the
guard, so `set -u` cannot abort there. Every `exit`/`sys.exit` statement is one-for-one identical
between v2.7.1 and HEAD in all three gating hooks — same codes, same order, only line numbers
shifted.

**Behavioural.** 22 fixtures × 2 hooks, each fixture a real git repo, driven with real hook JSON
(Edit, Write, apply_patch, malformed JSON, non-file tools):

```
check-hitl-context.sh   EXIT-CODE DIFFS: 0
check-domain-boundary.sh EXIT-CODE DIFFS: 0
```

Every distinct branch was confirmed reached, not skipped, by reading v2.7.1's distinct message on
each: `HITL BLOCKED: status 'de...`, `HITL CONTEXT MISMATCH`, `HITL: change GH-1 looks...`,
`HITL CONTEXT INCOMPLETE`, `HITL BLOCKED: no active...`, `HITL_PARSE_ERROR`. The two rewritten
advisory blocks in `check-domain-boundary.sh` were exercised directly: outside-`allowed_paths`
still exits 0 and still prints the note; the malformed-change-file path still exits 1 with
`HITL_PARSE_ERROR` on both versions.

`check-platform-ready.sh`: 6 register states (absent / empty / unparseable / zero-items /
open-gap-no-waiver / flag-false) × 6 environment strings (production, staging, dev, canary,
`"Production "`, PROD) — 0 exit-code diffs.

**Encoding.** The one plausible way a message rewrite un-gates a deploy is emoji inside the deploy
gate's embedded Python: a `UnicodeEncodeError` there would be caught by the outer
`except Exception` handler, which calls `block()` again and re-raises, degrading a hard exit 2 to
an uncaught exit 1. It does not happen — Python's stderr uses `backslashreplace`:

```
enc=ascii old -> exit 2 | HITL DEPLOY BLOCKED: platform readiness register is not parseable.
enc=ascii new -> exit 2 | \U0001f512 Deploy stopped: I cannot read the readiness register...
```

Ugly under a non-UTF-8 stderr, but the gate holds. The CHANGELOG's *"Same gates, same exit codes,
same enforcement"* is **true**, and it is the claim in this release I tried hardest to break.

---

## 3. The CHANGELOG's account of what happened

### FINDING C-1 (HIGH) — the corrected claim is still false

> Four rounds of independent review found **fourteen CRITICAL findings, every one of them inside
> those three rules** — and none anywhere else in this release. ... That mistake was published in
> an earlier draft of this note, which is corrected here.

`.hitl/reviews/incoming/consequence-round4.md:40` is **CRITICAL-1 — "Nothing that validated before
this release fails now" is false in five shapes**. Its mechanisms are `canonical_lens()` and the
sibling-record findings loop. Both **ship at HEAD**. Neither is `LENS_FLOOR`, `UNVERIFIED_FIX`, or
the carry-forward. I reproduced its alias-pair shape independently above without having read it
first — it is a live defect in shipped code, not a defect in a removed rule.

Round 4's CRITICAL-3 and CRITICAL-4 *were* inside the carry-forward and are genuinely gone with it.
CRITICAL-1 is not. So "every one of them inside those three rules — and none anywhere else in this
release" is false, in the same class as the claim the sentence two lines later says it corrected.
This is the statement the priority list flagged, and it did not survive checking.

### FINDING C-2 (MEDIUM) — the count cannot be verified from anything that ships

Tracked records carry two rounds and six CRITICALs, three of them still `status: open`:

```
round1-bypass       CRITICAL 2 (B1 fixed, B2 accepted)
round1-consequence  CRITICAL 1 (C1 fixed)
round1-upgrade      CRITICAL 0
round2-bypass       CRITICAL 2 (R2B-1 open, R2B-2 open)
round2-consequence  CRITICAL 1 (R2C-1 open)
TOTAL across records: {'CRITICAL': 6, 'HIGH': 10, 'MEDIUM': 4}
```

Rounds 3 and 4 have **no record at all**. They exist only as `.md` files under
`.hitl/reviews/incoming/`, which this release's own `.gitignore` excludes (`.gitignore:27`). The
entry closes with *"read the earlier rounds — the trail is kept for that reason."* Half the rounds
it cites are not in the trail. I am not asserting fourteen is the wrong number; I am reporting that
nothing that ships can confirm or refute it, which for a paragraph whose subject is a previously
published miscount is the property that matters.

### FINDING C-3 (MEDIUM) — every committed record cites evidence that does not ship

All five tracked records point their `reproduction:` field into the gitignored directory:

```
$ grep -n "incoming/" .hitl/reviews/*.yaml
round2-bypass.yaml:20:      reproduction: See .hitl/reviews/incoming/bypass-round2.md R2-1, escalating fixtures.
round1-upgrade.yaml:46:     reproduction: See .hitl/reviews/incoming/upgrade-round1.md F6-F12.
round1-consequence.yaml:50: reproduction: See .hitl/reviews/incoming/consequence-round1.md MEDIUM-1..3, LOW-1..3.
round1-bypass.yaml:35:      reproduction: See .hitl/reviews/incoming/bypass-round1.md B-3, B-5, B-6, B-7, B-8.
round2-consequence.yaml:28: reproduction: See .hitl/reviews/incoming/consequence-round2.md fixtures C, D, E.

$ git check-ignore -v .hitl/reviews/incoming/consequence-round2.md
.gitignore:27:.hitl/reviews/incoming/   .hitl/reviews/incoming/consequence-round2.md
```

The record is the durable artifact and it is committed. Its evidence is unreachable to everyone
except the machine that ran the review. `reproduction` is the field the skill calls the difference
between a finding and a guess; on a fresh clone every one of them dereferences to nothing. Not a
blocker, but it is the release's own governance state contradicting its own doctrine.

### FINDING C-4 (LOW) — the stated icon vocabulary does not match what ships

> Icons are a small set marking state — 🔒 paused, 🧭 where you are, **⚠️ irreversible**, ✅ done

The only ⚠️ in the five hooks is `check-domain-boundary.sh:88`, on *"I could not read
.hitl/current-change.yaml"* — an advisory PostToolUse parse error that blocks nothing and is fully
reversible. Nothing irreversible is marked in this release.

### FINDING C-5 (LOW) — "All 46 of them" is not reproducible

Counted four ways across the five hooks: 44 non-empty message lines removed by the diff; 56
non-empty message-emitting lines present at v2.7.1; 52 including blank `echo "" >&2` separators;
14 `HITL `-prefixed strings. None is 46. I am reporting this as unverifiable rather than false —
"a message" is not pinned down. *"including the four inside the deploy gate's Python block"* is
exactly right: 4, verified.

### FINDING C-6 (LOW) — "The portal had not moved since v2.1.1"

`site/index.html` changed on 2026-07-20 (`5be9905`, GitHub nav link, #34) and 2026-08-14
(`f436c51`, getting-started page, #74). The substance — that the portal still *described* v2.1.1,
which is what commit `afa27dd`'s own message says — is true. The literal sentence is not.

### Claims I checked and found true

- *"Same gates, same exit codes, same enforcement."* Verified in §2.
- The catalog generator's allowlist is a build failure now: `check_order_covers()` raises
  `SystemExit` and is called before `build_fragment()`; `release` was added to `ORDER`.
- The nav overwrite is fixed: `SHELL` now carries Getting started and the GitHub link.
- *"the hooks carry their icons as literal characters and read no configuration"* —
  `grep -rn "preferences|HITL_ICONS|no-icons"` over `ai/claude/hooks/` returns nothing.
- *"They stay out of the breadcrumb and statusline"* — no breadcrumb or statusline file appears in
  `diff v2.7.1..HEAD`; `statusline-hitl.sh` carries none of the new glyphs.
- *"The gate read one reviewer's findings per round"* — real, and really fixed (S1/S2/S3 above show
  v2.7.1 passing on a sibling's defect purely because of `sorted(os.listdir())`).
- The four rewritten messages inside the deploy gate's Python block: exactly four.

---

## 4. `.hitl/reviews/incoming/` — sound, with one consequence

- **Escape.** The path is composed by the orchestrator from a lens it picked out of a fixed
  13-entry catalog; the reviewer receives a literal string, never a template it fills. A subagent
  holding Write can write anywhere in the filesystem regardless of this convention, so the
  convention grants no capability it did not already have. No escape vector introduced.
- **Trusted input.** The orchestrator does read reviewer-authored markdown back into its own
  context, which is model-generated text becoming input to a process that writes governance
  records. `SKILL.md` Step 4 is the correct mitigation and it is explicit: *"for each finding, do
  not act on it yet — reproduce it yourself. Reviewers are wrong sometimes, confidently"*,
  *"Does not reproduce → say so explicitly in the record"*, and *"A missing file means unknown,
  never failed."* A careless or hostile report cannot become a finding without the orchestrator
  reproducing it first, and cannot become a *fix* without the user answering the triage step.
  Sound as written.
- **Gate interaction.** `.hitl/` is in `EXEMPT_PREFIXES`, so a reviewer writing its report does not
  trip `UNCOMMITTED_CHANGES`. That exemption is unchanged from v2.7.1 and is documented in the
  brief template. Correct.
- The one consequence is C-3: gitignoring the directory is what severs every committed record from
  its evidence.

---

## 5. Worst thing that happens to a real project that upgrades and changes nothing else

Nothing is destroyed, exposed, or made unrecoverable. Grepping the whole shipped diff over `ai/`,
`ci/` and `tools/` for `rm -rf`, `rm -f`, `shutil.rmtree`, `os.remove`, `os.unlink`,
`git reset --hard`, `git clean`, `truncate`, and `--force` returns no introduced call. No file is
rewritten in place, no credential path is touched, no network call is added. Hook gating is
byte-for-byte equivalent in behaviour (§2), so no edit that was blocked becomes allowed and no edit
that was allowed becomes blocked.

The worst realistic outcome is bounded and recoverable: a team mid-release runs
`/hitl:dev-update`, which overwrites `ci/adversarial/check_review.py`, and their release gate
starts blocking on a **historical** round they cannot re-run — an alias pair (`consequence` +
`destructiveness`), a numbered second reviewer, or a sibling record with a typo'd severity that
happened to sort first. The remedy is to edit a review record that was already written and
already signed off. One line, but it is history being rewritten to satisfy a gate, and the note
they were told to read says only two of the four codes they might see, and tells them a legacy lens
name is safe.

That is a bad afternoon, not a bad outcome. It does not justify holding the release on its own.

---

## Verdict

**DO NOT SHIP** — on the CHANGELOG, not the code.

The four features are sound. The gate change is strictly additive across 6047 tested record shapes
with zero fail-open regressions. The five hooks are behaviourally identical to v2.7.1 on every
reachable path. The reviewer-report channel is well-designed and its trusted-input handling is
correct. Those are clean results and I would say so plainly if the release were only those things.

What blocks it is C-1. The paragraph that exists specifically to correct a previously published
false claim about where the findings were contains a false claim about where the findings were.
Round 4's consequence CRITICAL-1 is in `canonical_lens()` and the sibling-record loop, both of
which ship, and I reproduced its alias-pair shape independently. Shipping a release whose own
account of its review is wrong in the sentence about its review being wrong is the failure this
project's doctrine is built around.

### Smallest change that fixes it

Three edits to the 2.8.0 CHANGELOG entry. No code change.

1. **"On three checks that are not in this release":** delete *"and none anywhere else in this
   release."* State the count the trail can support, or say where rounds 3 and 4 live. (C-1, C-2)
2. **"Note for existing projects":** change *"Two things newly block"* to name all four codes, and
   amend *"a legacy lens name ... validate[s] exactly as they did on 2.7.1"* to add the alias-pair
   case: a legacy name is safe alone, and blocks beside its modern equivalent in the same round.
   (H-1, H-2)
3. **"HITL stops talking like a compiler":** drop or correct *"⚠️ irreversible"* — nothing
   irreversible is marked. (C-4)

Worth doing but not ship-blocking: either un-ignore `.hitl/reviews/incoming/`, or rewrite the five
`reproduction:` fields so a committed record cites evidence a fresh clone can reach. (C-3)
