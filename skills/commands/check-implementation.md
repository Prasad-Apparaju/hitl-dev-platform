---
description: Code review — compare implementation against the approved LLD and system manifest for spec adherence, edge case coverage, and convention compliance
argument-hint: "[LLD path or issue number]"
---

Use the `spec-conformance-reviewer` agent to review the implementation for $ARGUMENTS.

Read the LLD at the path provided, the implementation files in the approved manifest domain, and the test files in `tests/`. Do not approve until:
- Implementation matches all LLD method signatures, error modes, and preconditions
- All LLD edge cases are handled in the code
- No cross-cutting conventions from `system-manifest.yaml` are violated
- No new behavior exists in the code that is not described in the LLD
