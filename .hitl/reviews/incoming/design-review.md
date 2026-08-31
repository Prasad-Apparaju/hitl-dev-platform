# Review — docs/design/right-sizing/01-design.md

Two things I checked by running them, because the plan's answer depends on them:

- **What "the floor" actually is.** Resolved `crit`/`crit_by_tier` from `ai/shared/workflows.yaml`
  through `ci/first-pass/check_skips.py:resolve_crit`. For the `development` workflow the floor is
  **tier 0/1: `deploy`, `promote`** · tier 2: those plus `integration_verify` · tier 3: eight steps.
  §4 makes "the floor" the entire short path, so its size is load-bearing.
- **What the ledger demands of a skip.** `check_skips.py` requires an actor *and* a reason **per
  skipped step**, and raises `INCOMPLETE_PLAN` if a floor/`no_omit` step is absent from the plan
  entirely. §5 claims the existing order already works, so this is the interface the plan must meet.

## 1. Does the demo.sh change get a short path?

Yes, but only because of a question the plan leaves open, and the path it lands on is not a defined
length.

- Intake asks the domain. `scripts/demo.sh` is in none → **outside the model**. Good.
- Risk gate. The signal list is "secrets, auth, deploy, migration"; the change adds
  `FIRECRAWL_API_KEY=`. §9.2 has not decided whether the signal is asked, inferred from paths, or read
  off the issue. Inferred from a keyword, this fires and returns the full 31 steps — the exact case
  the plan exists to fix. Asked, it does not. The plan is a coin-flip on its own motivating example.
- The cut. "The floor, and nothing else claimed." At tier 0/1 that is `deploy` + `promote`, neither of
  which applies to a demo script — so the honest answer is roughly **zero steps**, not a short plan.
  At tier 3 the same words mean eight. The plan never says which tier an outside-the-model change
  resolves against, and "the floor" is only defined relative to one.

So: short, yes. Deliberately sized, no.

## Five points, ranked

**1. "Outside the model" merges two very different cases, and this stops the plan working.**
§1's argument — we cannot see it, so ceremony over it is theatre — is true of a demo script and false
of undeclared source. §7 states it plainly: a project with no manifest is *always* outside the model.
That is every greenfield project built through `start-from-prd` until code exists to generate a
manifest from, and every brownfield repo before `start-brownfield` runs. Under this plan those
projects build their first product on `deploy`+`promote` and nothing else: no tests, no gates, no
review, no risk keyword tripped. Concretely: editing `ci/first-pass/check_skips.py` — the validator
that blocks PRs — is in no domain in most repos, and loosening it takes the floor path. The plan
inherits the *shape* of the mistake it names in §1, mirrored: the earlier version gave the least
knowledge the most process; this one gives it the least. The shipped probe had the discriminator the
plan dropped — non-source versus source-under-a-domain, plus "however small a diff under a manifest
domain looks, this probe says nothing about it". Undeclared is not the same as non-source.

**2. There is no step-to-manifest mapping, and this stops the plan working.**
§2 gives three examples (docs when `lld`, compatibility when a facade moves, integration when
something depends on this domain) for a 31-step catalog. Nothing says what triggers the other 28.
Worse, §2 and §4 describe two different mechanisms: §2 is a per-step predicate, §4 is four coarse
buckets (floor / short / longer / everything). Both cannot be the design. Until one is chosen and the
per-step table exists, nobody can build this. §7's "no ranking data, so nothing is shortened" points
at a third mechanism — per-step metadata in the workflow file — that appears nowhere else in the
document.

**3. Nothing verifies the domain claim, and this is worth deciding.**
The domain is answered by a human at intake, and it is now the sole gate to the short path. Step 3b
already warns that "nothing downstream re-checks the declaration against what the change actually
touches"; the plan adds a second self-declared input with the same property, and drops the one
evidence-based signal shipped today (the `git diff` probe). The manifest has `files` globs and
requests usually name a path, so the cheap fix is available: match the named paths against every
domain's `files` at intake, and re-check the real diff at merge — if a domain owned it, the
shortening was wrong. §9.4 asks who is accountable; accountability without a check is just a name.

**4. The ledger interface is undecided, and this is worth deciding.**
§1 says record it once, with "outside the model" as the reason. The validator wants an actor and a
reason on each skipped step and refuses a plan with a floor or `no_omit` step missing. So: does the
cut emit ~20 per-step skip records sharing one reason (ledger, resurfacing and the PR gate keep
working) or a genuinely shorter plan (`INCOMPLETE_PLAN`, and TDD's `no_omit` protection silently
evaporates)? §5 asserts the existing plumbing works; that holds only under the first reading, and the
plan reads like the second.

**5. §8 and §9.1 contradict each other, and this is minor but has to go.**
§8 puts "any change to what the floor protects" out of scope. §9.1 asks whether the outside-the-model
floor should be "something smaller" than the tier floor. Given point 1 above, the answer likely runs
the other way — the floor for undeclared *source* needs to be bigger, not smaller — but either way one
of the two sections is wrong.

## 2. Where it wrongly shortens

Point 1 is that example: any change in a project that has not yet generated its manifest, including
source, including the first build of a whole product. §7 records it as a release-note item. It is not
a release-note item; it is the plan turning itself off for the projects that have most recently
onboarded.

## 3. What is missing before anyone builds

Points 1–4, in that order. The plan's own §9 list is real but not the blocking set: §9.2 (risk
detection, plus carrying forward "naming a key is not moving one", which resolves the motivating
case and is absent here) and §9.1 (the floor, and which tier it resolves against) are blocking; §9.3
is a nice-to-have.

---

this plan does not, because "outside the model" is not the same thing as "cheap to change" — as
written it hands every un-manifested project, source and all, a two-step floor, and it never says
which of the 31 steps a declared domain actually buys back.

One line on shipped code, not a finding about this plan: `ai/claude/start-change/right-sizing.md`
says non-source is anything outside a domain's `paths`; the schema field is `files`.
