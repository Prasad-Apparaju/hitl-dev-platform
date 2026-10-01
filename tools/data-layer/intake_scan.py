#!/usr/bin/env python3
"""Intake scan (FR-31, DL-1, LLD §3.1): what the repo says its data sources are.

Reads config, compose, settings, IaC and env files; proposes one source per distinct database or
service with the file and line it was declared in. Connection-string VALUES are never copied, only
their scheme and host. The person edits the proposal into sources.yaml at Stage 1.

Usage:
    python3 tools/data-layer/intake_scan.py --root . --out docs/02-design/data/sources.proposed.yaml
"""
from __future__ import annotations

import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dl_common import dump_yaml, now_utc, stamp  # noqa: E402

SCHEMES = {
    "postgres": "relational", "postgresql": "relational", "mysql": "relational", "mariadb": "relational",
    "sqlite": "relational", "mssql": "relational", "oracle": "relational", "jdbc": "relational",
    "mongodb": "document", "mongodb+srv": "document", "snowflake": "warehouse", "bigquery": "warehouse",
    "redshift": "warehouse", "databricks": "warehouse",
}
IMAGES = {
    "postgres": "relational", "mysql": "relational", "mariadb": "relational", "mssql": "relational",
    "mongo": "document", "couchdb": "document", "cockroachdb": "relational", "clickhouse": "warehouse",
}
ENV_SUFFIXES = ("_URL", "_URI", "_DSN", "_HOST", "_CONNECTION_STRING")
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build", ".hitl", "evidence"}
CONFIG_EXT = (".env", ".yml", ".yaml", ".toml", ".ini", ".cfg", ".py", ".json", ".tf", ".properties")


def kebab(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def scan(root: str) -> list[dict]:
    found: dict[str, dict] = {}
    env_to_key: dict[str, str] = {}      # DATABASE_URL -> orders-db, learned where both appear on one line
    pending: list[tuple[str, str, str]] = []   # (env name, fallback key, where) resolved at the end

    def add(key: str, kind: str, where: str):
        key = kebab(key) or "unknown"
        e = found.setdefault(key, {"id": "src:%s" % key, "kind": kind, "declared_from": []})
        if e["kind"] == "unknown" and kind != "unknown":
            e["kind"] = kind
        if where not in e["declared_from"]:
            e["declared_from"].append(where)

    for dirpath, dirs, names in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for n in sorted(names):
            if not (n.endswith(CONFIG_EXT) or n.startswith(".env") or n in ("dbt_project.yml", "profiles.yml")):
                continue
            path = os.path.join(dirpath, n)
            rel = os.path.relpath(path, root).replace(os.sep, "/")
            try:
                with open(path, encoding="utf-8", errors="replace") as f:
                    lines = f.read().splitlines()
            except OSError:
                continue
            compose = n in ("docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml")
            service = None
            for i, line in enumerate(lines, 1):
                where = "%s:%d" % (rel, i)
                if compose:
                    m = re.match(r"^  ([A-Za-z0-9_.-]+):\s*$", line)
                    if m:
                        service = m.group(1)
                    m = re.match(r"^\s+image:\s*([A-Za-z0-9_./-]+)", line)
                    if m and service:
                        img = m.group(1).split("/")[-1].split(":")[0]
                        if img in IMAGES:
                            add(service, IMAGES[img], where)
                # connection strings: scheme://[user@]host[:port]/db ; the value is not copied
                for m in re.finditer(r"\b([a-z][a-z0-9+]*)://(?:[^@\s/\"']*@)?([A-Za-z0-9_.${}-]+)", line):
                    scheme, host = m.group(1).lower(), m.group(2)
                    if scheme in SCHEMES:
                        key = kebab(host.strip("${}") or scheme)
                        add(key, SCHEMES[scheme], where)
                        for em in re.finditer(r"\b([A-Z][A-Z0-9_]*(?:%s))\b" % "|".join(ENV_SUFFIXES), line):
                            env_to_key.setdefault(em.group(1), key)
                # env var names that look like a source
                for m in re.finditer(r"\b([A-Z][A-Z0-9_]*(?:%s))\b" % "|".join(ENV_SUFFIXES), line):
                    name = m.group(1)
                    if re.search(r"://", line):
                        continue  # the connection string above already named it
                    base = re.sub(r"(%s)$" % "|".join(ENV_SUFFIXES), "", name)
                    if base:
                        pending.append((name, base, where))
                if n == "dbt_project.yml" and re.match(r"^name:\s*", line):
                    add("dbt-%s" % line.split(":", 1)[1].strip().strip("'\""), "dbt", where)
                if re.search(r'resource\s+"(aws_rds_|aws_db_instance|aws_docdb|snowflake_database|google_bigquery_dataset)', line):
                    m = re.search(r'resource\s+"([a-z_]+)"\s+"([A-Za-z0-9_-]+)"', line)
                    if m:
                        kind = "document" if "docdb" in m.group(1) else ("warehouse" if ("snowflake" in m.group(1) or "bigquery" in m.group(1)) else "relational")
                        add(m.group(2), kind, where)
            if os.path.basename(dirpath) in ("dags",) and n.endswith(".py"):
                add("orchestrator-%s" % os.path.basename(dirpath), "orchestrator", rel + ":1")
    for name, base, where in pending:
        if name in env_to_key:
            add(env_to_key[name], found[env_to_key[name]]["kind"], where)
        else:
            add(base, "unknown", where)
    return [found[k] for k in sorted(found)]


def proposal(root: str, at=None) -> dict:
    at = at or now_utc()
    sources = [{"id": "src:app", "kind": "code", "declared_from": ["."], "environment": "dev",
                "in_scope": True, "access": {"granted": "read_only", "mode": "offline"},
                "status": "proposed", "notes": "the repository itself"}]
    for s in scan(root):
        sources.append({"id": s["id"], "kind": s["kind"], "declared_from": s["declared_from"],
                        "environment": "dev", "in_scope": True,
                        "access": {"granted": "read_only", "mode": "offline"},
                        "status": "proposed", "notes": "set environment, access and in_scope; rename if the host is not the name people use"})
    return {"schema_version": "1.0", "written_by": {"stage": "intake", "at": stamp(at)}, "sources": sources}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="docs/02-design/data/sources.proposed.yaml")
    a = ap.parse_args(argv)
    doc = proposal(a.root)
    dump_yaml(a.out, doc)
    print("intake_scan: %d source(s) proposed -> %s" % (len(doc["sources"]), a.out))
    for s in doc["sources"]:
        print("  %-24s %-12s %s" % (s["id"], s["kind"], ", ".join(s["declared_from"][:3])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
