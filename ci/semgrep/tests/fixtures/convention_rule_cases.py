"""Fixture for the generalized convention rules (issue #46). NOT executable code.

These rules used to encode ONE customer's stack: Qdrant with a `brand_id` tenant key, a helper
named `retry_external_call` with clients named `httpx_client`, and a `MutatingTool` base class.
None of that is a HITL concept — `qdrant` appears in zero HITL docs and `MutatingTool` only under
docs/examples/. Shipping them to every customer meant rules that were either dead weight or, once
the path scoping was removed, actively wrong for anyone with a different stack.

So the fixture deliberately uses vendors and names NO HITL customer is assumed to share: Pinecone
and Weaviate rather than Qdrant, `tenacity`/`backoff` rather than a bespoke wrapper, and
`SideEffectingTool` rather than `MutatingTool`, and four web frameworks rather than FastAPI alone.
If a rule only passes here because it was written against one project's identifiers, it fails.

Line numbers are asserted by ci/semgrep/test_convention_rules.py — update EXPECTED if you edit.
"""

import re
import requests
from fastapi import Request


# ── vector-search-must-be-tenant-scoped ───────────────────────────────────────────────────

# BAD: unfiltered similarity search returns every tenant's vectors
hits = pinecone_index.query(vector=vec, top_k=10)

# BAD: a different vendor, same defect
more = weaviate_client.search(query=q, limit=10)

# OK: filtered — the rule does not care WHICH key, only that the query is scoped
ok1 = pinecone_index.query(vector=vec, top_k=10, filter={"org_id": org})
ok2 = weaviate_client.search(query=q, where={"path": ["tenant"]})
ok3 = chroma_collection.similarity_search(query=q, filter={"customer": cid})

# OK: not a vector store at all — must never be flagged
m = re.search(r"\d+", line)
rows = elasticsearch.search(index="logs", body=q)


# ── external-calls-must-be-retried ────────────────────────────────────────────────────────

def fetch_bare(url):
    # BAD: library-level HTTP call with no retry policy anywhere
    return requests.get(url)


@backoff.on_exception(backoff.expo, Exception)
def fetch_decorated(url):
    # OK: retry-shaped decorator
    return requests.get(url)


@tenacity.retry(stop=tenacity.stop_after_attempt(3))
def fetch_tenacity(url):
    # OK: a different retry library
    return requests.post(url, json={})


def fetch_wrapped(url):
    # OK: inside a retry-shaped helper call
    return call_with_retry(lambda: requests.get(url))


def read_local(path):
    # OK: not an HTTP call
    return open(path).read()


# ── request-body-must-be-validated (framework-neutral) ────────────────────────────────────

@router.post("/assets")
async def fastapi_bad(request: Request):
    # BAD: FastAPI/Starlette raw body straight into business logic
    return await handle_asset(await request.json())


@app.route("/flask", methods=["POST"])
def flask_bad():
    # BAD: Flask
    return create_thing(request.get_json())


def django_bad(request):
    # BAD: Django
    return save_record(request.POST)


async def aiohttp_bad(request):
    # BAD: aiohttp
    return await store(await request.json())


@router.post("/ok/pydantic")
async def ok_pydantic(request: Request):
    # OK: validated by a pydantic model before use
    return await handle_asset(AssetCreate.model_validate(await request.json()))


def ok_marshmallow():
    # OK: marshmallow schema
    return create_thing(AssetSchema().load(request.get_json()))


def ok_drf(request):
    # OK: DRF serializer
    return save_record(AssetSerializer(data=request.data))


def ok_project_validator(request):
    # OK: a project's own validator — matched by name, not by library
    return save_record(validate_asset_payload(request.POST))


def ok_not_a_request(cfg):
    # OK: `cfg` is not a request object
    return handle_asset(cfg.data)


# ── side-effecting-tool contracts ─────────────────────────────────────────────────────────

class PublishPostTool(SideEffectingTool):
    # BAD: no idempotency_key, no _describe_plan — note the base is NOT `MutatingTool`
    def execute(self, post_id):
        return self.api.publish(post_id)


class DeleteRecordTool(WritingTool):
    # OK: both contracts satisfied under a third base-class name
    def _describe_plan(self, record_id):
        return f"would delete {record_id}"

    def execute(self, record_id, idempotency_key=None):
        return self.repo.delete(record_id, key=idempotency_key)


class SearchTool(ReadOnlyTool):
    # OK: read-only tools carry no side effect, so neither contract applies
    def execute(self, query):
        return self.index.lookup(query)
