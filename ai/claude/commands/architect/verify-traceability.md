---
description: Integration verification — confirm the issue → design → code → tests chain is intact, E2E + smoke suite pass, and the impact brief is complete before merge
argument-hint: "[PR link or issue number]"
---

Use the `spec-conformance-reviewer` agent to verify traceability for $ARGUMENTS.

Confirm the chain is unbroken: GitHub issue exists → design PR merged → implementation matches LLD → tests cover the spec → impact brief reviewed → rollout plan approved.

Then verify the following gates before marking integration verify complete:

1. **Traceability chain** — every acceptance criterion in the PRD traces to a test in the test registry.

2. **E2E Playwright** — confirm `required_evidence.e2e_tests_pass: true` in `.hitl/current-change.yaml`. If missing or false, block: "E2E tests have not passed QA verify. Step 22 must complete before integration verify."

3. **Smoke suite** — confirm `required_evidence.smoke_suite_pass: true` in `.hitl/current-change.yaml`. If missing or false, run the smoke suite now:
   ```bash
   npx playwright test tests/e2e/smoke/ --project=chromium
   npx playwright test tests/e2e/smoke/ --project="iPhone 15"
   npx playwright test tests/e2e/smoke/ --project="Pixel 7"
   ```
   Block if any journey fails. The smoke suite exercises the full new-customer flow across all registered features — a failure here means the build is not promotable regardless of unit test results.

4. **Ops scripts verified** — confirm `ops_scripts.verified_at` exists in `.hitl/current-change.yaml` and `ops_scripts.rollback_covered: true`. If missing, run `/hitl:ops-verify-scripts <change-ID> --level full` now. Block if any failure is returned — broken or untested ops scripts are a merge blocker, not a post-merge fix.

5. **Cross-slice composition** — if this change spans multiple decision-packet slices, verify the slices compose correctly end-to-end (no interface mismatches between them).

Do not approve traceability if any of these gates are open.
