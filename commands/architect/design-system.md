---
description: Design a new system from a PRD — domain decomposition, system manifest, HLDs, ADRs, LLDs, and HITL process bootstrap
argument-hint: "[path to PRD]"
---

Invoke the `architect/design-system` skill with $ARGUMENTS.

This command takes a PRD and produces the complete system foundation: domain decomposition, `docs/system-manifest.yaml`, system-level HLDs, foundational ADRs, domain-level LLDs, and the HITL process bootstrap (CLAUDE.md, convention checks, CI, issue templates).

After this command completes, use `/architect:design-feature` for individual changes going forward.

Do not proceed past domain decomposition without explicit architect confirmation — domain boundary decisions cascade through every subsequent artifact.
