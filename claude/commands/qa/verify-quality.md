---
description: Post-handoff independent quality verification — verify the running build against acceptance criteria, run exploratory testing, and block or approve promotion to Ops
argument-hint: "[feature name or build link]"
---

Invoke the `qa-verify-quality` skill with $ARGUMENTS.

Do not approve promotion if any acceptance criterion is unmet, any incident regression can be reproduced, or any open defect has not been re-verified. Use `/qa:report-defect` to file any blocking issues found.
