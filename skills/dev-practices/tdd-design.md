# TDD as a Design Tool — Reference

> Use the `/tdd` skill to run this process. This file is the conceptual reference.

## The Core Insight

TDD in this process is not just about test-first coding. Tests are a **design refinement loop**: AI generates maximum test coverage from the spec, humans inject domain expertise, and the combined test suite reveals gaps in the design — BEFORE any implementation code is written.

Writing "test that publishing fails gracefully when Instagram rate-limits at 100 posts/day" is more precise than writing that requirement in an LLD paragraph — and it's executable. Tests are a higher-fidelity spec language than prose.

## The Three-Phase Loop

```
Phase A — AI generates tests (RED)
    AI reads the LLD + test plan + manifest facade contracts.
    Generates: happy paths, error paths, edge cases, preconditions,
    boundary entity validation, contract compliance.
    Goal: MAXIMUM coverage of the SPEC, not the code (which doesn't exist yet).

Phase B — Humans refine tests
    Developer reviews every test — the highest-value human step in the build phase:
    • Adds edge cases AI missed ("what if the API returns 429 mid-carousel
      but the first 2 images already published?")
    • Adds integration scenarios from domain knowledge
    • Removes trivial or wrong tests
    • Challenges assumptions ("this test assumes retry will succeed,
      but what if the budget is exhausted?")

Phase C — Tests improve the design
    AI analyzes combined test suite for LLD gaps:
    • A test for rate-limit handling but no rate-limit section in LLD
      → ADD rate-limit behavior to the LLD
    • A test for a retry path but no retry spec
      → ADD retry behavior to the LLD
    • A test implying a precondition not in the manifest
      → ADD the precondition to the manifest facade
    The LLD and manifest are UPDATED before any code is generated.
```

Then: verify RED → generate code → verify GREEN → refactor.

## Why This Order Matters

| Without TDD-as-design | With TDD-as-design |
|-----------------------|---------------------|
| LLD written → code generated → tests written → gaps found → code rewritten | LLD written → tests generated → humans add cases → gaps found → LLD improved → code generated right the first time |
| LLD-to-code gap discovered AFTER code exists | LLD-to-code gap discovered BEFORE code exists |
| Humans review prose for completeness | Humans review executable tests — more concrete, less ambiguous |

## Contract Tests from the Manifest

For changes touching domain boundaries, generate contract tests from the manifest's facade APIs:

```python
# Generated from manifest facade: publishing.instagram_publish
def test_instagram_publish_returns_tool_result_with_external_id():
    """Contract: PublishResult must contain external_id."""
    result = await tool.execute(image_url="...", caption="...", idempotency_key="test:0:ig")
    assert result.success
    assert "external_id" in result.data

def test_instagram_publish_rejects_missing_idempotency_key():
    """Contract: precondition — idempotency_key required."""
    result = await tool.execute(image_url="...", caption="...")
    assert not result.success
    assert "idempotency_key" in result.error

def test_instagram_publish_returns_cached_on_duplicate_key():
    """Contract: idempotent — second call with same key returns cached."""
    await tool.execute(image_url="...", caption="...", idempotency_key="test:0:ig")
    result = await tool.execute(image_url="...", caption="...", idempotency_key="test:0:ig")
    assert result.data["cached"] is True
```

## When Tests Surface LLD Gaps

| Test the developer added | LLD gap revealed | LLD update |
|--------------------------|------------------|------------|
| `test_publish_fails_on_rate_limit` | LLD doesn't mention rate limits | Add "rate-limited requests return 429; caller retries via resilience.retry_external_call" |
| `test_carousel_with_11_images_rejected` | LLD doesn't specify image count limit | Add "carousel accepts 2-10 images; >10 raises ValueError" |
| `test_publish_in_plan_mode_returns_preview` | LLD doesn't mention plan mode | Add "in PLAN mode, returns dry-run preview via _describe_plan()" |

Each gap → LLD update → the spec gets more precise → generated code is more correct.
