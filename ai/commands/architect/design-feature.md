---
description: Guide the architect through steps 3–9 — impact analysis, HLD, LLD, slice decomposition, and decision packet assembly
argument-hint: "[issue number or feature description]"
---

Invoke the `architect/design-feature` skill with $ARGUMENTS.

This command covers the architect's full design journey: impact analysis (step 3), ROI trigger check (step 4), HLD and LLD generation with approval gates (step 5), IaC planning (step 6), test case planning (step 7), training plan stub (step 8), and decision packet assembly (step 9).

Do not proceed to implementation until all decision packets are approved and `.hitl/current-change.yaml` shows `approvals.architecture: approved`.
