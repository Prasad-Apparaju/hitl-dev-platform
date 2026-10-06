# Test categories — the E2E stubs and the smoke suite

Read from Phase 1 of `/hitl:dev-tdd`, categories C and D. The rules are in SKILL.md; this is the
shape of the files those rules produce.

## C. Playwright E2E tests — file structure

   File structure:
   ```typescript
   import { test, devices } from '@playwright/test';
   const iphone = devices['iPhone 15'];
   const android = devices['Pixel 7'];

   test.skip('pending environment');

   test.describe('<feature-name>', () => {
     test.use({ ...iphone }); // repeat block with android
     test('<AC description — desktop>', async ({ page }) => { /* ... */ });
   });
   ```

   > **Note on native mobile apps:** Playwright covers web browsers and mobile web (responsive/PWA). If the feature includes a native iOS or Android app, those require Appium or Detox: flag that in the test plan.

## D. Smoke suite contribution — layout, the journey file, and `setup.ts`

   Structure:
   ```
   tests/e2e/smoke/
     setup.ts          ← creates a brand-new test customer (signup → onboard)
     teardown.ts       ← deletes test customer and all associated data
     journeys/
       <existing>.spec.ts
       <feature-name>.spec.ts   ← ADD THIS for the current feature
   ```

   The journey file must:
   - Assume a fresh customer created in `setup.ts` — no pre-existing data
   - Exercise the feature's primary user action end-to-end via browser
   - Assert the visible outcome the PM would verify
   - Run on desktop Chrome + `devices['iPhone 15']` + `devices['Pixel 7']`
   - NOT be skipped — smoke suite always runs

   If `tests/e2e/smoke/setup.ts` does not exist yet, create it now. It must:
   - Hit the app's signup flow via Playwright (real browser, not API)
   - Complete onboarding
   - Store the created customer's credentials in a fixture file for the journey tests to consume
   - Be idempotent (safe to run repeatedly; tears down previous test customer first)
