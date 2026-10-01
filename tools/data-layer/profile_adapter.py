#!/usr/bin/env python3
"""Profile adapter (FR-31, DL-3, DL-8, LLD §3.3): what the store says.

Offline mode (the tested path, ADR-4) reads exports the person produced: JSON lines or CSV, one
file per store, plus an optional schema dump. Live mode runs the same profiling over a
`ReadOnlyFetch` object that has no write method; it refuses to start unless sources.yaml carries a
complete authorization for the source, and a missing driver is recorded as access not obtained.
`--no-samples` keeps values out of the evidence file.

Usage:
    python3 tools/data-layer/profile_adapter.py --source src:orders-db --export exports/ --schema-dump exports/orders-schema.sql
    python3 tools/data-layer/profile_adapter.py --source src:orders-db --live --driver postgres
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from typing import Iterable, Protocol

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dl_common import (EXIT_OK, EXIT_REFUSED, EXIT_UNREADABLE, authorization_ok, envelope,  # noqa: E402
                       find_source, load_yaml, log_run, parse_ts, set_source_status, write_evidence)


class ReadOnlyFetch(Protocol):
    """The only interface a live driver implements. There is no write method to call."""

    def stores(self) -> list[str]: ...

    def count(self, store: str) -> int: ...

    def sample(self, store: str, n: int) -> Iterable[dict]: ...


# ---------------------------------------------------------------------------
# Offline exports
# ---------------------------------------------------------------------------

class ExportFetch:
    """ReadOnlyFetch over a folder of <store>.jsonl / <store>.csv files."""

    def __init__(self, folder: str):
        self.folder = folder
        self.calls: list[str] = []

    def _path(self, store: str) -> str | None:
        for ext in (".jsonl", ".json", ".csv"):
            p = os.path.join(self.folder, store + ext)
            if os.path.isfile(p):
                return p
        return None

    def locator(self, store: str) -> str:
        p = self._path(store) or os.path.join(self.folder, store)
        return os.path.relpath(p).replace(os.sep, "/")

    def stores(self) -> list[str]:
        self.calls.append("stores")
        return sorted({os.path.splitext(n)[0] for n in os.listdir(self.folder) if n.endswith((".jsonl", ".json", ".csv"))})

    def rows(self, store: str) -> Iterable[dict]:
        p = self._path(store)
        if not p:
            return []
        if p.endswith(".csv"):
            with open(p, newline="", encoding="utf-8") as f:
                return list(csv.DictReader(f))
        out = []
        with open(p, encoding="utf-8") as f:
            text = f.read()
        if p.endswith(".json"):
            d = json.loads(text)
            return d if isinstance(d, list) else []
        for line in text.splitlines():
            if line.strip():
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return out

    def count(self, store: str) -> int:
        self.calls.append("count")
        return len(list(self.rows(store)))

    def sample(self, store: str, n: int) -> Iterable[dict]:
        self.calls.append("sample(%d)" % n)
        return list(self.rows(store))[:n]


# ---------------------------------------------------------------------------
# Profiling: counts, presence, key candidates, key overlap
# ---------------------------------------------------------------------------

def _present(v) -> bool:
    return v is not None and v != "" and v != [] and v != {}


def profile(fetch: ReadOnlyFetch, stores: list[str], sample_rows: int, keys: list[tuple[str, str, str, str]],
            locator_of, no_samples: bool) -> list[dict]:
    items = []
    samples: dict[str, list[dict]] = {}
    for store in stores:
        total = fetch.count(store)
        rows = [r for r in fetch.sample(store, sample_rows) if isinstance(r, dict)]
        samples[store] = rows
        sampled = total > len(rows)
        items.append({"kind": "count", "locator": locator_of(store), "data": {"store": store, "rows": total, "sampled": sampled}})
        if rows:
            fields = []
            for r in rows:
                for k in r:
                    if k not in fields:
                        fields.append(k)
            pct = {f: round(100.0 * sum(1 for r in rows if _present(r.get(f))) / len(rows), 1) for f in fields}
            items.append({"kind": "field_presence", "locator": locator_of(store), "data": {"store": store, "sample": len(rows), "present_pct": pct}})
            uniq = [f for f in fields if pct[f] == 100.0 and len({json.dumps(r.get(f), sort_keys=True, default=str) for r in rows}) == len(rows)]
            if uniq:
                items.append({"kind": "key_candidates", "locator": locator_of(store), "data": {"store": store, "unique_fields": uniq}})
            if not no_samples:
                pass  # values never leave the sample; the evidence file carries counts and presence only
    for left_store, left_field, right_store, right_field in keys:
        if left_store not in samples and right_store not in samples:
            continue
        for st in (left_store, right_store):      # the other side of a key pair is sampled, never profiled
            if st not in samples:
                try:
                    samples[st] = [r for r in fetch.sample(st, sample_rows) if isinstance(r, dict)]
                except Exception:
                    samples[st] = []
        lrows = samples.get(left_store) or []
        rrows = samples.get(right_store) or []
        if not lrows or not rrows:
            continue
        lv = {json.dumps(r.get(left_field), sort_keys=True, default=str) for r in lrows if _present(r.get(left_field))}
        rv = {json.dumps(r.get(right_field), sort_keys=True, default=str) for r in rrows if _present(r.get(right_field))}
        matched = len(lv & rv)
        items.append({"kind": "key_overlap", "locator": locator_of(right_store),
                      "data": {"left": "%s.%s" % (left_store, left_field), "right": "%s.%s" % (right_store, right_field),
                               "left_rows": len(lv), "matched": matched, "share": round(matched / len(lv), 3) if lv else 0.0}})
    return items


def parse_schema_dump(path: str) -> list[dict]:
    """CREATE TABLE statements -> ddl items with columns, primary key, unique and foreign keys."""
    items = []
    with open(path, encoding="utf-8") as f:
        text = f.read()
    for m in re.finditer(r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([A-Za-z_][\w.]*)\s*\((.*?)\);", text, re.S | re.I):
        table, body = m.group(1), m.group(2)
        line = text[:m.start()].count("\n") + 1
        cols, pk, uniq, fks = [], [], [], []
        for raw in re.split(r",\s*\n", body):
            c = raw.strip().rstrip(",")
            if not c:
                continue
            um = re.match(r"UNIQUE\s*\((.*?)\)", c, re.I)
            if um:
                uniq.append([x.strip() for x in um.group(1).split(",")])
                continue
            pm = re.match(r"PRIMARY\s+KEY\s*\((.*?)\)", c, re.I)
            if pm:
                pk += [x.strip() for x in pm.group(1).split(",")]
                continue
            fm = re.match(r"FOREIGN\s+KEY\s*\((\w+)\)\s+REFERENCES\s+(\w+)\s*\((\w+)\)", c, re.I)
            if fm:
                fks.append({"field": fm.group(1), "to": "%s.%s" % (fm.group(2), fm.group(3))})
                continue
            cm = re.match(r"(\w+)\s+([A-Za-z]+(?:\([^)]*\))?)", c)
            if not cm:
                continue
            cols.append([cm.group(1), cm.group(2).lower()])
            if re.search(r"PRIMARY\s+KEY", c, re.I):
                pk.append(cm.group(1))
            rm = re.search(r"REFERENCES\s+(\w+)\s*\((\w+)\)", c, re.I)
            if rm:
                fks.append({"field": cm.group(1), "to": "%s.%s" % (rm.group(1), rm.group(2))})
        data = {"table": table, "columns": cols, "primary_key": pk}
        if uniq:
            data["unique"] = uniq
        if fks:
            data["foreign_keys"] = fks
        items.append({"kind": "ddl", "locator": "%s:%d" % (os.path.relpath(path).replace(os.sep, "/"), line), "data": data})
    return items


def keys_from_code_evidence(path: str) -> list[tuple[str, str, str, str]]:
    out = []
    if not path or not os.path.exists(path):
        return out
    for it in load_yaml(path).get("items") or []:
        if isinstance(it, dict) and it.get("kind") == "join":
            d = it.get("data") or {}
            k = d.get("keys") or {}
            if d.get("left") and d.get("right") and k.get("left") and k.get("right"):
                out.append((d["left"], k["left"], d["right"], k["right"]))
    return out


# ---------------------------------------------------------------------------
# Live mode: the same profiling behind a fetch layer, only with authorization
# ---------------------------------------------------------------------------

def live_fetch(driver: str, dsn: str):
    """Import the driver lazily; a missing one is reported, never raised to the caller."""
    if driver == "mongo":
        import pymongo  # noqa: F401  (ImportError is the caller's signal)
        client = pymongo.MongoClient(dsn, serverSelectionTimeoutMS=5000)
        db = client.get_default_database()

        class _M:
            def stores(self):
                return sorted(db.list_collection_names())

            def count(self, store):
                return db[store].estimated_document_count()

            def sample(self, store, n):
                return [{k: v for k, v in d.items() if k != "_id"} for d in db[store].find({}, limit=n)]
        return _M()
    if driver == "postgres":
        import psycopg  # noqa: F401
        conn = psycopg.connect(dsn, options="-c default_transaction_read_only=on")

        class _P:
            def stores(self):
                with conn.cursor() as c:
                    c.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY 1")
                    return [r[0] for r in c.fetchall()]

            def count(self, store):
                with conn.cursor() as c:
                    c.execute('SELECT count(*) FROM "%s"' % store.replace('"', ''))
                    return c.fetchone()[0]

            def sample(self, store, n):
                with conn.cursor() as c:
                    c.execute('SELECT * FROM "%s" LIMIT %d' % (store.replace('"', ''), int(n)))
                    cols = [d[0] for d in c.description]
                    return [dict(zip(cols, r)) for r in c.fetchall()]
        return _P()
    raise ImportError("no driver named %r" % driver)


def run_live(data_dir: str, source: str, fetch: ReadOnlyFetch, sample_rows: int, keys, at, no_samples: bool, src: dict) -> tuple[int, str]:
    """Profile a live store through `fetch`. The caller has already checked authorization."""
    assert not any(hasattr(fetch, m) for m in ("insert", "update", "delete", "write", "execute")), "a fetch with a write method is refused"
    env = src.get("environment", "unknown")
    stores = fetch.stores()
    items = profile(fetch, stores, sample_rows, keys, lambda s: "%s/%s" % (source, s), no_samples)
    access = {"mode": "live", "environment": env, "read_only": True,
              "authorization": {"by": src["authorization"]["by"], "at": src["authorization"]["at"]}}
    doc = envelope("profile", source, at, "profile_adapter.py", access, items)
    path = write_evidence(data_dir, doc, at)
    calls = ["stores", "count", "sample(%d)" % sample_rows]
    log_run(data_dir, "profile_adapter", source, "live", env, True, calls, "ok", at=at)
    set_source_status(data_dir, source, "extracted")
    return EXIT_OK, path


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", required=True)
    ap.add_argument("--data-dir", default="docs/02-design/data")
    ap.add_argument("--export", help="folder of <store>.jsonl or .csv exports (offline mode)")
    ap.add_argument("--schema-dump", help="a .sql dump of CREATE TABLE statements (offline mode)")
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--driver", help="mongo or postgres; any other name is recorded as a missing driver")
    ap.add_argument("--dsn-env", default="", help="environment variable holding the read-only DSN (live)")
    ap.add_argument("--code-evidence", help="code evidence file whose join items name the key pairs to test")
    ap.add_argument("--keys", action="append", default=[], help="left_store.field=right_store.field (repeatable)")
    ap.add_argument("--stores", help="comma-separated store names to profile (default: every export)")
    ap.add_argument("--sample-rows", type=int, default=500)
    ap.add_argument("--no-samples", action="store_true")
    ap.add_argument("--taken-at")
    a = ap.parse_args(argv)
    at = parse_ts(a.taken_at)
    keys = keys_from_code_evidence(a.code_evidence)
    for k in a.keys:
        m = re.fullmatch(r"(\w+)\.(\w+)=(\w+)\.(\w+)", k)
        if m:
            keys.append(m.groups())
    src = find_source(a.data_dir, a.source)
    env = (src or {}).get("environment", "offline-export")

    if a.live:
        ok, reason = authorization_ok(src)
        if not ok:
            log_run(a.data_dir, "profile_adapter", a.source, "live", env, True, None, "refused", reason, at=at)
            print("profile_adapter: refused, %s. Record the AUTHORIZED reply for %s in sources.yaml first." % (reason, a.source))
            return EXIT_REFUSED
        dsn = os.environ.get(a.dsn_env or "", "")
        try:
            fetch = live_fetch(a.driver or "", dsn)
        except ImportError as e:
            log_run(a.data_dir, "profile_adapter", a.source, "live", env, True, None, "refused", "driver_missing", at=at)
            set_source_status(a.data_dir, a.source, "declared-not-extracted")
            print("profile_adapter: driver not available (%s); %s stays declared, not extracted." % (e, a.source))
            return EXIT_UNREADABLE
        except Exception as e:  # cannot connect: the source stays unextracted, nothing else happens
            log_run(a.data_dir, "profile_adapter", a.source, "live", env, True, None, "refused", "connect_failed", at=at)
            print("profile_adapter: could not connect (%s); %s stays declared, not extracted." % (e.__class__.__name__, a.source))
            return EXIT_UNREADABLE
        code, path = run_live(a.data_dir, a.source, fetch, a.sample_rows, keys, at, a.no_samples, src)
        print("profile_adapter: live profile -> %s" % path)
        return code

    if a.schema_dump:
        if not os.path.isfile(a.schema_dump):
            log_run(a.data_dir, "profile_adapter", a.source, "offline", env, True, None, "refused", "schema_dump_missing", at=at)
            return EXIT_UNREADABLE
        items = parse_schema_dump(a.schema_dump)
        doc = envelope("schema", a.source, at, "profile_adapter.py", {"mode": "offline", "environment": env, "read_only": True}, items)
        path = write_evidence(a.data_dir, doc, at)
        log_run(a.data_dir, "profile_adapter", a.source, "offline", env, True, ["schema"], "ok", at=at)
        print("profile_adapter: %d table(s) from the schema dump -> %s" % (len(items), path))
    if a.export:
        if not os.path.isdir(a.export):
            log_run(a.data_dir, "profile_adapter", a.source, "offline", env, True, None, "refused", "export_missing", at=at)
            return EXIT_UNREADABLE
        fetch = ExportFetch(a.export)
        stores = fetch.stores()
        if a.stores:
            wanted = [s.strip() for s in a.stores.split(",") if s.strip()]
            stores = [s for s in stores if s in wanted]
        items = profile(fetch, stores, a.sample_rows, keys, fetch.locator, a.no_samples)
        doc = envelope("profile", a.source, at, "profile_adapter.py", {"mode": "offline", "environment": env, "read_only": True}, items)
        path = write_evidence(a.data_dir, doc, at)
        log_run(a.data_dir, "profile_adapter", a.source, "offline", env, True, ["count", "sample(%d)" % a.sample_rows], "ok", at=at)
        print("profile_adapter: %d item(s) over %d store(s) -> %s" % (len(items), len(stores), path))
    if a.schema_dump or a.export:
        set_source_status(a.data_dir, a.source, "extracted")
        return EXIT_OK
    print("profile_adapter: give --export and/or --schema-dump, or --live")
    return EXIT_REFUSED


if __name__ == "__main__":
    sys.exit(main())
