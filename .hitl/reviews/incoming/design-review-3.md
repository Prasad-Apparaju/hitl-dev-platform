# Design review 3 — right-sizing, progress-and-retro

Two docs, three questions, five points, ranked.

**Checked, because the answers turn on it:** the catalog tally in right-sizing §4 is right — across the
34 development steps: 21 `always`, 5 profile-keyed, 4 path-keyed, 3 `multi_domain`, 1 tag. The floor
arithmetic is right too: floor ∪ `no_omit` gives 4 at tier 1, 5 at tier 2, 10 at tier 3, 9 without
`impact`. The diagnosis of what is broken today is sound. Also checked: `#93` is open and scoped
"tier 2+ only"; the tier is set at intake step 3b from the issue text, before anything is read.

## 1. The fast track is never defined. This stops it working.

§4 names three sets. Set one is the workflow. Set two, "the ones that apply", is derived by `engages`,
and §4's rules section is entirely about that derivation. Set three, "the ones needed now" — the fast
track, the product — has no rule anywhere in either doc. `forgo_cost` is explicitly described as
ordering the steps already outside it, not selecting them. Steps 4, 5 and 6 all read from a set that
step 4 does not produce: the recommendation line, the delta shown to the user, and the untick prompt
each presuppose it exists.

## 2. The rules key off the area's paperwork, not the change. This stops it working.

§4 lists the six facts a rewritten `engages` keys off: has a design doc, has dependents, publishes an
interface, emits events, has tests, needed a source read. Five of the six are properties of the *area*
and constant across every change to it. Walking the two changes:

**Small change, well-documented domain.** Every predicate answers yes, because the domain is
well-documented. "Applies" is near the whole workflow, and with no fast-track rule (point 1) nothing
narrows it. A one-line fix in the best-covered area of the system gets the longest plan in the system.
That is #97's complaint reproduced by a different mechanism than `API_KEY` — and it prices documenting
an area at "every future change to it costs more".

**The change that should get the full plan.** A new feature has no owning area. §3 routes that to
"the manifest is missing an area", which "offers full scale or asks you to name the area". Neither
rescues it: a new area has no lld, no dependents, no interface, no events, no tests, so nearly every
rule answers no and full scale — "the ones that apply" — is close to empty. The one change that most
needs `test_plan`, `packet` and `adv_design` is the one the rules exclude. The tier floor is the only
thing left holding it up, and see point 4.

## 3. Two removal paths, opposite record requirements. Worth deciding.

Unticking one rule-placed step in §5 costs an interruption, a disposition and a reason, and the PR
checker refuses without both. Taking the fast track removes the same class of step wholesale, and §4
records nothing (the only stated non-record is for choosing full scale). So either the fast track is
the unrecorded bulk version of the thing §5 refuses to let you do quietly, or fast-track drops do
prompt — in which case the cheap option asks more questions than the thorough one and §5's stated
friction concern is understated, not watched. The docs do not say which, and there is a third path
they never mention: intake step 4b's tier 0/1 batch-decline with one canned reason.

## 4. The only risk control is set before anything is read. Worth deciding.

§4 rests the whole safety story on the tier: "risk is handled by the tier and by nothing else." The
tier is proposed from the issue text and human-confirmed before impact analysis runs. Neither doc says
whether impact analysis may revise it. So the step that actually discovers blast radius cannot change
the one control that responds to blast radius. Related ordering: §2 claims to run "before anything is
read or planned", yet its write destinations depend on which area owns the change and which workflow
applies — both outputs of §3.

## 5. The feedback loop is gated by the thing it corrects, and reads a record nobody writes. Worth deciding.

The retro is a catalog step with its own `engages`, so it falls out of the fast track — on exactly the
fast-tracked changes whose sizing feedback right-sizing depends on to fix its admittedly-wrong rules.
And its "how the sizing turned out" part has to compare a rule against what impact analysis found, but
the change-file inventory in the retro doc lists no impact-analysis record; right-sizing §3 asks for
provenance ("say which of the three the answer came from") without naming an artifact. Two smaller
ones in the same doc: the boundary check is stated as a "should" rather than decided, and progress
updates extend an open `#93` whose block is tier-2+ while this trigger has no tier qualifier.

## Answers

**Flow.** The chain breaks in three places: §2 writes to destinations §3 determines; §4 consumes a set
it never derives; §5's record requirement is bypassed by §4's own recommendation. The two docs agree
where they overlap except on the impact-analysis record, which one needs and the other does not
produce.

**Buildable?** No. Three things are missing to the point of unbuildable: the fast-track predicate, the
tier's relationship to impact analysis, and the artifact impact analysis writes that the rules and the
retro both read. Everything else is fillable by a careful implementer.

*One line on existing code, not a finding about these designs: `workflows.yaml` declares
`total: 31` for a development workflow with 34 steps.*
