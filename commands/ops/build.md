---
description: Build the application from a specified branch — verify CI status, produce an artifact, and confirm build readiness before deployment
argument-hint: "[branch name or PR number]"
---

Invoke the `ops-build` skill with $ARGUMENTS.

Do not mark the build ready until artifact integrity is verified and the smoke check passes.
