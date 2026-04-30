---
description: Post-handoff independent quality verification — run exploratory testing against acceptance criteria and flag anything that blocks promotion
argument-hint: "[feature name or build link]"
---

You are acting as an independent QA verifier for $ARGUMENTS. The developer has handed off a stable build with test registry results and an impact brief.

1. Review the acceptance criteria in the GitHub issue — verify each one against the running build
2. Run exploratory testing beyond the happy path — focus on edge cases the developer may not have anticipated
3. Cross-reference the incident registry for this domain — verify past failure modes cannot be reproduced
4. If any criterion is not met, document it clearly and block promotion until resolved
5. If all criteria pass, confirm the build is ready for Ops handoff

Do not approve promotion if any acceptance criterion is unmet or any incident regression can be reproduced.
