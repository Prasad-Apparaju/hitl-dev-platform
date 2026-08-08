"""Fixture for the non-SQL convention rules (issue #46). NOT executable code.

Each rule gets a violating case and a compliant case. Before #46 these five rules were scoped to
`V2/app/**` — one product repo's layout — so in any other project they matched no files and always
passed. The scope is gone; these fixtures are what keeps them honest instead.

Deliberately laid out under a conventional-but-different structure (no `V2/`, no `app/`) so a
regression that reintroduces path scoping fails here.

Line numbers are asserted by ci/semgrep/test_convention_rules.py — update EXPECTED if you edit.
"""

from fastapi import Request


# ── qdrant-must-filter-brand-id ───────────────────────────────────────────────────────────

# BAD: no query_filter, so nothing constrains the result set to one tenant
hits = qdrant_client.search(collection_name="assets", query_vector=vec)

# BAD: attribute access on self still binds the client
more = self.vector_store.search(collection_name="assets", query_vector=vec)

# OK: filtered by brand
ok = qdrant_client.search(collection_name="assets", query_vector=vec, query_filter=brand_filter)

# OK: not a vector search at all — must never be flagged (this is why the receiver is constrained)
match = re.search(r"\d+", line)
found = elasticsearch.search(index="logs", body=q)


# ── external-calls-must-use-retry-wrapper ─────────────────────────────────────────────────

async def fetch_unwrapped(url):
    # BAD: external call with no retry wrapper
    return await httpx_client.get(url)


async def fetch_wrapped(url):
    # OK: wrapped
    return await retry_external_call(lambda: http_client.get(url))


async def fetch_internal(url):
    # OK: not one of the external client names
    return await db_session.get(url)


# ── controller-must-use-pydantic-models ───────────────────────────────────────────────────

@router.post("/assets")
async def create_asset_bad(req: Request):
    # BAD: raw Request reaches business logic unvalidated
    return await handle(await req.json())


@router.post("/assets/validated")
async def create_asset_ok(body: AssetCreate):
    # OK: pydantic model
    return await handle(body)


# ── mutating-tool-must-implement-describe-plan / -must-have-idempotency-key ───────────────

class DeleteAssetToolBad(MutatingTool):
    # BAD: no _describe_plan, and execute() takes no idempotency_key
    def execute(self, asset_id):
        return self.repo.delete(asset_id)


class DeleteAssetToolOk(MutatingTool):
    # OK: both contracts satisfied
    def _describe_plan(self, asset_id):
        return f"would delete {asset_id}"

    def execute(self, asset_id, idempotency_key=None):
        return self.repo.delete(asset_id, key=idempotency_key)
