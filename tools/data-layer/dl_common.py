#!/usr/bin/env python3
"""Shared pieces for the data-layer adapters (FR-31, LLD §3): the evidence envelope, run.log,
sources.yaml lookup and exit codes. Standard library plus PyYAML only (ADR-4)."""
from __future__ import annotations

import datetime as dt
import os
import sys

try:
    import yaml
except ImportError:  # pragma: no cover
    print("ERROR: pyyaml required. Run: pip install pyyaml")
    sys.exit(2)

VERSION = "1.0.0"
EXIT_OK, EXIT_REFUSED, EXIT_UNREADABLE = 0, 2, 3


def now_utc() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0)


def stamp(t: dt.datetime) -> str:
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def file_stamp(t: dt.datetime) -> str:
    return t.strftime("%Y%m%dT%H%M")


def parse_ts(v: str | None) -> dt.datetime:
    if not v:
        return now_utc()
    return dt.datetime.fromisoformat(v.replace("Z", "+00:00"))


def load_yaml(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        d = yaml.safe_load(f)
    return d if isinstance(d, dict) else {}


def dump_yaml(path: str, obj) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(obj, f, sort_keys=False, allow_unicode=True, width=100)


def envelope(evidence_type: str, source: str, taken_at: dt.datetime, adapter: str, access: dict,
             items: list[dict], extra: dict | None = None) -> dict:
    """The LLD §2.7 envelope. Items are {id, kind, locator, data}; ids are ev:<source>/<type>/<nnnn>."""
    src = source.split(":", 1)[1] if source.startswith("src:") else source
    out = {"schema_version": "1.0", "evidence_type": evidence_type, "source": source,
           "taken_at": stamp(taken_at), "adapter": {"name": adapter, "version": VERSION}, "access": access}
    if extra:
        out.update(extra)
    out["items"] = [{"id": "ev:%s/%s/%04d" % (src, evidence_type, i + 1), "kind": it["kind"],
                     "locator": it["locator"], "data": it["data"]} for i, it in enumerate(items)]
    return out


def evidence_path(data_dir: str, source: str, evidence_type: str, taken_at: dt.datetime) -> str:
    src = source.split(":", 1)[1] if source.startswith("src:") else source
    return os.path.join(data_dir, "evidence", src, "%s-%s.yaml" % (evidence_type, file_stamp(taken_at)))


def write_evidence(data_dir: str, doc: dict, taken_at: dt.datetime) -> str:
    """One file per source and type; a new run replaces the previous file for the same pair."""
    path = evidence_path(data_dir, doc["source"], doc["evidence_type"], taken_at)
    folder = os.path.dirname(path)
    if os.path.isdir(folder):
        for n in os.listdir(folder):
            if n.startswith(doc["evidence_type"] + "-") and n.endswith(".yaml") and os.path.join(folder, n) != path:
                os.remove(os.path.join(folder, n))
    dump_yaml(path, doc)
    return path


def log_run(data_dir: str, adapter: str, source: str, mode: str, env: str, read_only: bool,
            calls: list[str] | None, result: str, reason: str | None = None, at: dt.datetime | None = None) -> None:
    os.makedirs(data_dir, exist_ok=True)
    parts = ["%s %s %s mode=%s env=%s read_only=%s" % (stamp(at or now_utc()), adapter, source, mode, env,
                                                       "true" if read_only else "false")]
    if calls:
        parts.append("calls=%s" % ",".join(calls))
    parts.append("result=%s" % result)
    if reason:
        parts.append("reason=%s" % reason)
    with open(os.path.join(data_dir, "run.log"), "a", encoding="utf-8") as f:
        f.write(" ".join(parts) + "\n")


def find_source(data_dir: str, source: str) -> dict | None:
    path = os.path.join(data_dir, "sources.yaml")
    if not os.path.exists(path):
        return None
    for s in load_yaml(path).get("sources") or []:
        if isinstance(s, dict) and s.get("id") == source:
            return s
    return None


def set_source_status(data_dir: str, source: str, status: str) -> None:
    path = os.path.join(data_dir, "sources.yaml")
    if not os.path.exists(path):
        return
    doc = load_yaml(path)
    for s in doc.get("sources") or []:
        if isinstance(s, dict) and s.get("id") == source:
            s["status"] = status
    dump_yaml(path, doc)


def authorization_ok(src: dict | None) -> tuple[bool, str]:
    """DL-8: a live read needs a complete authorization whose environment is the source's."""
    if not src:
        return False, "no_source"
    au = src.get("authorization")
    if not isinstance(au, dict) or any(not au.get(k) for k in ("by", "at", "environment", "statement")):
        return False, "no_authorization"
    if au.get("environment") != src.get("environment"):
        return False, "environment_mismatch"
    if str(au.get("statement")).strip().upper() != "AUTHORIZED":
        return False, "no_authorization"
    return True, ""
