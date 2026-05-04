---
description: Deploy a verified build artifact to a target environment following the approved rollout plan
argument-hint: "[environment: staging|canary|production] [branch or artifact reference]"
---

Invoke the `ops-deploy` skill with $ARGUMENTS.

Do not deploy until the rollout plan is approved, IaC changes are applied, and the build artifact is verified.
