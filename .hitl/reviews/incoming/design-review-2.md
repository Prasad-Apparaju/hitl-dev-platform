# Review — right-sizing a change (docs/design/right-sizing/01-design.md)

Reviewing the plan only. Five points, ranked.

## 1. The plan does not say what happens to the selection that already ships. This stops the plan working.

Steps 4 and 5 — a locked floor, a ranked tickable list, untick-and-record — are already built and
shipped: `ai/claude/start-change/selection.md`, `ai/claude/start-change/SKILL.md` Step 4b, and
`ci/first-pass/plan_select.py` / `rank.py`, which render exactly the "Selected — untick any / what
you'd lose" list this design describes as new. The design never names any of them. So a builder
cannot tell whether steps 4–5 replace that surface, feed it, or sit beside it — and if they sit
beside it, a user is offered the same 31 choices three times (intake fast/full, Step 4b disposition
menu, post-impact selection) with nothing saying which is authoritative or what happens when they
disagree. The non-goals section resolves this for impact analysis ("both can exist") and for nothing
else. Two composition theories also collide unacknowledged: the design derives the fast track from
manifest facts; the shipped ranker derives it from `forgo_cost` × `engages` × incident history.

## 2. The fast track is three examples, and one of them names a step that does not exist. This stops the plan working.

"Compatibility is in" — there is no compatibility step in `ai/shared/workflows.yaml` (I grepped it;
this mattered because it is one of only three composition rules given). "Integration" maps to
`integration_verify`, "docs" to `docs`. That leaves roughly 28 steps — `conventions`, `review1`,
`review2`, `rerun`, `reconcile`, `qa_verify`, `verify_pr`, `rollout`, `impact_brief`, the whole
Post-Ship tail — with no rule at all. Since full scale is "everything", the difference between the
two options is undefined for nearly every step in the workflow. Two implementers ship two products.

## 3. "Tickable" cannot express what the ledger requires. This stops the plan working.

The ledger the validator reads carries a disposition per step — keep / starter / defer / decline —
and the generator refuses dispositions a step's criticality disallows (`SKILL.md` Step 4b table,
`is_allowed`). A binary untick has no mapping onto that. It also cannot express the design's own
must-have exception: "the test-first cycle, which can be thinned but never dropped" *is* the starter
disposition, so the UI as described cannot represent its own floor. Separately, every record needs a
reason and an actor or the validator blocks; the design says "which step, who, why" but a one-click
untick has no moment where "why" is supplied.

## 4. Walkthroughs. Both come out wrong, in opposite directions.

**Small change, well-documented domain** (add a field; domain has `lld`, `depends_on`, tests). Nothing
in the six steps establishes the tier, yet must-haves are defined as "the floor for this change's
tier". At the default tier 2 the floor plus `no_omit` is five steps: `red`, `green`,
`integration_verify`, `deploy`, `promote` (computed from the catalog via `resolve_crit`). Step 4
carefully adds `docs` and integration from the manifest facts — and step 5 lets all of it be unticked,
because only must-haves are locked. Code review, conventions, QA and verify-PR were never must-haves
at tier 2 to begin with. So the derivation in step 4 has no force, and the honest description of the
outcome is "the floor, plus whatever the user did not untick".

**Tier 3, full 31.** The floor is ten steps, full scale is 31, and that part behaves. The break is
earlier: step 3 sizes from the manifest *before* any code is read, and the shipped design put sizing
after impact analysis for a recorded reason — at intake there is nothing to diff, and `depends_on`
is hand-declared, not derived. The design asserts a manifest lookup suffices and adds "read source
where the change clearly goes beyond what the manifest describes", with no account of who can judge
"clearly" before reading anything. Reversing a prior decision is allowed; not mentioning it is the
problem, because the reason it was made still applies to exactly the changes that need 31 steps.

## 5. The four open decisions: two are real, two are minor, and the two that block are missing.

Decision 1 (no-domain fast track) is worth deciding. Decision 2 (risk) is worth deciding but half of
it is already answered — tier *is* the risk dial and already raises the floor; the open part is only
whether some categories forbid the fast track outright. Decisions 3 (how a must-have looks) and 4
(is the recommendation binding) are minor; neither changes what gets built. The two that would stop a
build are absent: where this lives relative to the shipped selection surface (point 1), and what an
untick writes (point 3).

---

Not about this plan, one line as permitted: `selection.md` opens with "Shown at intake once the ask
is understood… Called from Step 4" and then says sizing runs after impact analysis in the second
command — the shipped doc contradicts itself about where the selection happens, which may be part of
why this plan was written as if the surface did not exist.

**This could not be built as written, because the fast track is undefined for 28 of 31 steps, one of
its three stated rules names a step the catalog does not contain, and the plan does not say what
becomes of the selection mechanism it duplicates.**
