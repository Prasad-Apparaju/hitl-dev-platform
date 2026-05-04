---
description: Design-time test contribution — query incident registry for domain failure modes and produce test scenarios for the developer to include in the test plan before TDD starts
argument-hint: "[LLD path or GitHub issue number]"
---

Invoke the `qa-plan-tests` skill with $ARGUMENTS.

This is non-blocking input to the test plan. Regression-required scenarios (from past incidents) must be acknowledged by the developer before the TDD cycle starts.
