---
description: Architect human code review — the Architect Code Review step. Creates the GitHub PR with the review checklist, notifies the architect, and records their approve/revisions decision. Requires AI rounds 1 and 2 to be complete first.
argument-hint: "[change ID or issue number]"
---

Run `/hitl:architect-review-code` for $ARGUMENTS.

Create the GitHub PR with the AI findings summary and architect checklist in the description. The architect reviews on GitHub using line comments and the review UI. Record their decision (approved or revisions required) in `.hitl/current-change.yaml`.
