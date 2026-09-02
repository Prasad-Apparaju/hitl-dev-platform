# Design review 5 — right-sizing + progress-and-retro

**What I checked in the data** (not the prose): `ai/shared/workflows.yaml` has 8 workflows;
`development` = 34 steps, `platform` = 17, smallest = 5 (`prd`, `migration_review`) — so "eight
workflows, 34 down to five" and "development (34) and platform (17)" are right. `step_costs` has 38
entries, every one with `protects` + `forgo_cost` + `engages`, **none** with `needed_now`. Across the
34 development steps the `engages` breakdown is exactly as claimed: 21 `always`, 4 `paths`, 5
`profiles`, 1 `tags`, 3 `multi_domain`. Runtime `crit`/`crit_by_tier` floors in `development`: tier 1
= 2 (`deploy`, `promote`), tier 2 = 3 (+`integration_verify`), tier 3 = 7 (+`impact`, `packet`,
`arch_review`, `qa_verify`, `rollout`). `step_costs` and `crit` exist **only** for the development
spine (`release` has `crit`; nothing else has either).

---

**1. This stops it working. Neither doc mentions First Pass, and right-sizing is a second copy of it
that the existing validator cannot certify.**
`start-change` Step 4b already elicits per-step dispositions (keep / starter / defer / decline),
tier-constrained, at intake, and writes `first_pass: true` + a `skips:` ledger; `check_skips.py`
enforces it fail-closed. Step 5 of right-sizing is the same elicitation, on the same steps, with
different rules, at a different moment, and neither doc names the flag, the ledger, or the checker.
The collision is not stylistic. Step 4b states "the actor on every resulting record is the person who
confirmed, **never the agent**"; right-sizing records fast-track exclusions as "HITL's decision …
no prompt". And the representation of an excluded step is unspecified, which is fatal both ways:
leave it out of `workflow.steps[]` and `PLAN_PRUNED` fires ("absent from the plan with no skip
record"); add a skip record for it and `LEDGER_STEPS` fires ("skip record references unknown step").
The only shape that certifies clean is step-present-with-`status: skipped` + a record carrying actor,
reason and a disposition — i.e. the ~24 omissions of a tier-1 fast track each need an accountable
human name, which is precisely the prompt the design says it does not ask for. `FP_UNDECLARED` sits
behind that. §3 anticipated one consumer (the floor-step-present check) and missed the rest.

**2. This stops it working. `platform` has none of the data the design assumes, and neither do the
other five non-development workflows.**
§4 names `platform` as one of the two workflows that gets the fast-track / full-scale choice. Its 17
steps carry no `crit`, no `crit_by_tier`, no `no_omit`, and no `step_costs` entry — so there is no
tier floor to lock, no `protects` sentence to show, no `forgo_cost` to order by, and no `engages` to
rewrite. The catalog also says platform progress lives in `docs/04-operations/platform-readiness.yaml`,
**not** `.hitl/current-change.yaml` — so it has no change file, no tier, and no ledger. Same for
brownfield / migration / migration_review / prd / docs, which §3 puts inside "runs on every
workflow" and progress-and-retro puts inside "floor at every tier": `floor` is not expressible in
those catalogs. §3's own arithmetic (33 → 34) adds the retrospective to `development` only.

**3. Worth deciding. "Risk is handled by the tier and by nothing else" does not hold, and the
tier-3 "ten" is where it shows.**
The three security/upgrade steps (`sec_design`, `cve_audit`, `pentest`) are `cond:` slots and are
**not** among the 34 runtime development steps; they are activated by the profile machinery the doc
itself declares dead ("five key off profiles … can never fire") and does not revive. So a tier-3
security change gets no security design review, no CVE audit and no pentest, and the tier is not
carrying the risk. The arithmetic gives it away: tier-3 floor inside the 34-step plan is 7, minus
`impact`, plus red/green/retrospective = **9**, not ten. §3's "ten → nine → ten" counts the three
conditional steps and excludes red/green; §4's "ten at tier 3" claims to include red/green. Two
different sets, both called ten, and the tier-1 (four → five) and tier-2 (five → six) figures — which
check out — are computed on the basis that yields nine.

**4. Worth deciding. Deleting `impact` from the plan takes more of `apply-change` with it than §3
says.** §3 says only that "`apply-change` loses its step 3". `apply-change` Step 7a — fold this
change's skips into `.hitl/skip-ledger.yaml` at the real scope, then resurface overlapping unresolved
entries — is anchored there and nowhere else, and `start-change` Step 6b says so explicitly: "entries
recorded before the workflow declares its area are marked project-wide; the `development` route
narrows them at its impact step." Delete the step and every skip stays project-wide forever. The
retrospective's "what is still open … feeds the resurfacing that already exists" is downstream of the
same producer. Step 1 (tier) and Step 2a (seed the change file) also move under this design.

**5. Worth deciding. The retrospective cannot both ask nobody anything and carry an approval line.**
Progress-and-retro defends floor-at-every-tier on the grounds that it "collects nothing and asks
nobody anything", then gives it "the same attribution line" — *Generated by Claude, approved by
&lt;name&gt;, &lt;date&gt;* — and says both it and the progress update "write to the issue". Under the
guarantee stated two sections earlier ("nothing goes out that you have not read"), publishing it needs
a reader and an approver, which is the ask it just disclaimed. Its destination is also never named:
progress updates are explicitly the "Where this stands" block and explicitly not a comment; the
retrospective is given neither.

---

**Could someone build this?** No, and two named things are why. (a) `needed_now` does not exist —
no field, no values, and no predicate language; it is defined as a rule over impact-analysis findings,
and the findings themselves are given only as three prose rows ("the findings / provenance / what the
rules concluded") with no field names, so there is nothing for a rule to key off. (b) The change-file
representation of an omitted step is unspecified, which is what makes point 1 unresolvable rather than
merely inconsistent. Everything else here is buildable from the text.

**Two walkthroughs.** *One-line fix in a well-documented area:* intake → restate → stub → impact finds
one area, no dependents, tests covering the changed behaviour → tier 1 → fast track. The locked five
(`deploy`, `promote`, RED, GREEN, retrospective) is right, and the shape is sensible. It goes wrong at
the ledger: 24 steps leave the plan and each needs an owned, reasoned, dispositioned record to
certify — the paperwork lands on the light path, which is #97's complaint. *Cross-domain feature on a
published interface:* impact finds three dependents and multi-domain, so `review2`, `impact_brief` and
`integration_verify` engage correctly, tier 3, both options offered. It goes wrong twice: `test_plan`,
`roi` and `training` are `profiles`-keyed and so can never fire — a genuine feature draws no test plan
even on full scale, which the rewrite must catch — and if the change is security-shaped, point 3
applies: nothing in the design can pull the three security steps into the plan.
