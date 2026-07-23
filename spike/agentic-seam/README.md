# Spike: the Advisor ↔ #10 seam (executable validation)

**Why this exists.** Seven paper review rounds kept failing on the same two claims because they are
*executable* properties that prose can't validate: `floor ≡ #10 activation`, and "the canonical state can
author a manifest #10 accepts." This spike settles them by **running** the seam, not asserting it.

It is a **prototype**, not the shipped implementation — a minimal but *real* version of the four pieces the
design specifies, sufficient to run three fixtures end-to-end:

| File | Role in the design |
|---|---|
| `activation.py` | THE single activation source (#10 LLD §6.0) — imported by both sides, so no copy drifts |
| `compose.py` | the Advisor composer — floor derived from the imported activation; PRIMARY vs SECONDARY ownership |
| `writer.py` | canonical state (`authored.*`) → a #10 manifest dict (Advisor LLD §5.1/§7.1.1) |
| `validator.py` | a real-but-minimal #10 validator (compound LLD §6) — required-field checks per activated check |
| `fixtures.py` | LOW / HIGH / DEEP canonical states with full authored output |
| `test_seam.py` | the three proofs |

## Run

```
cd spike/agentic-seam && python3 test_seam.py
```

## What it proves (all three fixtures pass)

1. **`floor ≡ activation`** — the composer's floor exactly equals the set of commands whose PRIMARY #10
   check activates on the manifest those commands author. No drift (the composer imports #10's predicates).
2. **`OWNERSHIP-COMPLETE`** — every activated blocking check (incl. `check_deep_agent`, `check_policy_refs`,
   `check_scope_grammar`) is owned by a floor command. The deep-agent counterexample (round-6 B1) passes.
3. **`AUTHOR-COMPLETE`** — the canonical state authors a manifest that passes #10's **real** validator
   (9 / 12 / 10 activated checks for LOW / HIGH / DEEP).

## What it caught that paper review missed

A concrete **B2 shape mismatch**: the Advisor's `authored.observability` was **flat**
(`{convention, hops, attributes, …}`) while #10 §4.3 **nests** them under `tracing:`. The writer passed it
straight through and #10 rejected it (`observability_convention`, `observability_hop_untraced`). Fixed in the
fixture and in the design doc (Advisor LLD §7.1). This is the exact class of transcription gap the reviews
kept predicting — found and fixed by execution in one sitting.

## Honest scope / limits

- The validator implements the **required-field / well-formedness** layer of each check, sufficient to prove
  the seam. It is not the full #10 validator (no exhaustive value-checking, no registries loading, no
  projections). The real implementation (#13/#16) supersedes it.
- Deferred mechanisms (result ingestion, saga required-when, universal eval coverage) are not modelled —
  they are out of the 2.2.0 core.
- The composer's `features_from_scenario` (prediction) and the validator's `features_from_manifest`
  (reality) are kept separate on purpose; the test asserts they agree for the fixtures.
