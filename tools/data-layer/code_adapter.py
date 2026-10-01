#!/usr/bin/env python3
"""Code adapter, Python (FR-31, DL-3, LLD §3.2): what the code says about the data.

Walks the repo's Python files with `ast` and writes one evidence file of type `code` for the source
(default src:app). Item kinds: orm_entity, store_literal, read, write, join, key_use, ddl. Files in
other languages are counted under coverage.files_skipped.other_language and never guessed from.

Usage:
    python3 tools/data-layer/code_adapter.py --root . --source src:app --data-dir docs/02-design/data
"""
from __future__ import annotations

import argparse
import ast
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dl_common import (EXIT_OK, envelope, log_run, now_utc, parse_ts, set_source_status,  # noqa: E402
                       write_evidence)

SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build", ".hitl", "evidence", "tests", "test"}
OTHER_LANG = (".js", ".ts", ".tsx", ".jsx", ".java", ".kt", ".go", ".rb", ".cs", ".php", ".scala", ".rs")
READ_METHODS = {"find": "find", "find_one": "find", "aggregate": "aggregate", "count_documents": "count",
                "select": "select", "query": "select", "get": "get", "filter": "select", "all": "select",
                "fetchall": "select", "fetchone": "select", "distinct": "select"}
WRITE_METHODS = {"insert_one": "insert", "insert_many": "insert", "insert": "insert", "add": "insert",
                 "update_one": "update", "update_many": "update", "replace_one": "update", "update": "update",
                 "save": "update", "bulk_write": "update", "delete_one": "delete", "delete_many": "delete",
                 "delete": "delete", "remove": "delete"}
SQL_RE = re.compile(r"\b(FROM|JOIN|INTO|UPDATE|TABLE)\s+([A-Za-z_][A-Za-z0-9_.]*)", re.I)
HANDLE_NAMES = {"db", "database", "mongo", "mongodb", "client", "conn", "connection", "store", "warehouse"}
HANDLE_CALLS = {"MongoClient", "AsyncIOMotorClient", "get_default_database", "get_database", "connect",
                "create_engine", "Database", "database"}


def _const_str(node) -> str | None:
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def _name(node) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _store_of_subscript(node) -> tuple[str | None, str | None]:
    """db["x"] -> ("x", None); db[f"x_{t}"] -> ("x_{t}", template)."""
    if not isinstance(node, ast.Subscript):
        return None, None
    sl = node.slice
    s = _const_str(sl)
    if s is not None:
        return s, None
    if isinstance(sl, ast.JoinedStr):
        parts = []
        for v in sl.values:
            if isinstance(v, ast.Constant):
                parts.append(str(v.value))
            elif isinstance(v, ast.FormattedValue):
                parts.append("{%s}" % (_name(v.value) or "x"))
        t = "".join(parts)
        return t, t
    return None, None


def _dict_keys(node) -> list[str]:
    if not isinstance(node, ast.Dict):
        return []
    return [k.value for k in node.keys if isinstance(k, ast.Constant) and isinstance(k.value, str)]


class FileScan(ast.NodeVisitor):
    def __init__(self, rel: str, orm_tables: dict[str, str], orm_fields: dict[str, list[str]]):
        self.rel = rel
        self.orm_tables = orm_tables          # class -> table
        self.orm_fields = orm_fields          # class -> fields
        self.assign: dict[str, ast.AST] = {}  # name -> last assigned value in the file
        self.store_vars: dict[str, str] = {}  # name -> store
        self.handles: set[str] = set(HANDLE_NAMES)   # names that hold a database handle
        self.items: list[dict] = []
        self.class_stack: list[str] = []

    def loc(self, node) -> str:
        return "%s:%d" % (self.rel, node.lineno)

    def emit(self, kind: str, node, data: dict):
        self.items.append({"kind": kind, "locator": self.loc(node), "data": data})

    # -- assignments: remember what names hold --------------------------------
    def _is_handle(self, node) -> bool:
        """db / client[...] / MongoClient(...).get_default_database(): a thing you index by store name."""
        if isinstance(node, ast.Name):
            return node.id in self.handles
        if isinstance(node, ast.Attribute):
            return node.attr in self.handles or self._is_handle(node.value)
        if isinstance(node, ast.Call):
            return (_name(node.func) in HANDLE_CALLS) or self._is_handle(node.func)
        if isinstance(node, ast.Subscript):
            return self._is_handle(node.value)
        return False

    def visit_Assign(self, node):
        for t in node.targets:
            if isinstance(t, ast.Name):
                self.assign[t.id] = node.value
                if self._is_handle(node.value) and not isinstance(node.value, ast.Subscript):
                    self.handles.add(t.id)
                store, tmpl = (None, None)
                if isinstance(node.value, ast.Subscript) and self._is_handle(node.value.value):
                    store, tmpl = _store_of_subscript(node.value)
                if store is None and isinstance(node.value, ast.Call):
                    store, tmpl = self._call_store(node.value)
                if store:
                    self.store_vars[t.id] = store
                    self.emit("store_literal", node.value, {"store": store, "how": ast.get_source_segment(self.src, node.value) or "", "template": tmpl})
        self.generic_visit(node)

    def _call_store(self, call: ast.Call) -> tuple[str | None, str | None]:
        """x.collection("c") / x.table("t") / Table("t", ...) -> store."""
        f = call.func
        attr = _name(f)
        if attr in ("collection", "table", "get_collection", "Table") and call.args:
            s = _const_str(call.args[0])
            if s:
                return s, None
        return None, None

    # -- ORM entities ---------------------------------------------------------
    def visit_ClassDef(self, node):
        table = None
        fields, keys, fks, rels = [], [], [], []
        django = any(_name(b) == "Model" for b in node.bases)
        for st in node.body:
            if isinstance(st, ast.Assign) and len(st.targets) == 1 and isinstance(st.targets[0], ast.Name):
                tname = st.targets[0].id
                if tname == "__tablename__":
                    table = _const_str(st.value)
                    continue
                v = st.value
                if isinstance(v, ast.Call):
                    fn = _name(v.func) or ""
                    if fn in ("Column", "mapped_column") or (django and fn.endswith("Field")):
                        fields.append(tname)
                        for kw in v.keywords:
                            if kw.arg == "primary_key" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                                keys.append(tname)
                        for arg in list(v.args) + [kw.value for kw in v.keywords]:
                            if isinstance(arg, ast.Call) and _name(arg.func) == "ForeignKey" and arg.args:
                                to = _const_str(arg.args[0])
                                if to:
                                    fks.append({"field": tname, "to": to})
                            if isinstance(arg, ast.Name) and django and fn == "ForeignKey":
                                fks.append({"field": tname, "to": arg.id})
                    elif fn == "relationship" and v.args:
                        to = _const_str(v.args[0]) or _name(v.args[0])
                        if to:
                            rels.append({"to": to, "kind": None})
            if isinstance(st, ast.ClassDef) and st.name == "Meta" and django:
                for m in st.body:
                    if isinstance(m, ast.Assign) and _name(m.targets[0]) == "db_table":
                        table = _const_str(m.value)
        if table is None and django and fields:
            table = node.name.lower()
        if table and fields:
            data = {"class": node.name, "table": table, "fields": fields, "keys": keys}
            if fks:
                data["foreign_keys"] = fks
            if rels:
                data["relationships"] = rels
            self.emit("orm_entity", node, data)
        self.class_stack.append(node.name)
        self.generic_visit(node)
        self.class_stack.pop()

    # -- calls: reads, writes, joins, key uses ----------------------------------
    def _receiver_store(self, func) -> str | None:
        if isinstance(func, ast.Attribute):
            base = func.value
            if isinstance(base, ast.Subscript) and self._is_handle(base.value):
                store, _ = _store_of_subscript(base)
                if store:
                    return store
            if isinstance(base, ast.Name):
                if base.id in self.store_vars:
                    return self.store_vars[base.id]
                if base.id in self.orm_tables:
                    return self.orm_tables[base.id]
            if isinstance(base, ast.Call):
                s, _ = self._call_store(base)
                if s:
                    return s
                return self._receiver_store(base.func)
        return None

    def _resolve(self, node):
        """A Name used as an argument resolves to its last assigned value."""
        if isinstance(node, ast.Name) and node.id in self.assign:
            return self.assign[node.id]
        return node

    def visit_Call(self, node):
        fn = _name(node.func)
        # SQL strings anywhere
        for arg in node.args:
            s = _const_str(arg)
            if s and SQL_RE.search(s) and re.search(r"\b(select|insert|update|delete|create)\b", s, re.I):
                self._sql(node, s)
        if fn == "select" and node.args:
            # select(Order.order_no, Order.promised_date) -> read orders fields
            cols = [(a.value.id, a.attr) for a in node.args if isinstance(a, ast.Attribute) and isinstance(a.value, ast.Name)]
            classes = {c for c, _ in cols}
            for c in sorted(classes):
                if c in self.orm_tables:
                    self.emit("read", node, {"store": self.orm_tables[c], "method": "select", "fields": [f for cc, f in cols if cc == c]})
        store = self._receiver_store(node.func) if isinstance(node.func, ast.Attribute) else None
        if store and fn in READ_METHODS:
            fields = []
            if len(node.args) >= 2:
                fields = _dict_keys(self._resolve(node.args[1]))
            if not fields and node.args and isinstance(self._resolve(node.args[0]), ast.List):
                fields = [e.value for e in self._resolve(node.args[0]).elts if isinstance(e, ast.Constant) and isinstance(e.value, str)]
            self.emit("read", node, {"store": store, "method": READ_METHODS[fn], "fields": fields})
            if node.args:
                self._filter(node, store, self._resolve(node.args[0]))
        elif store and fn in WRITE_METHODS:
            fields = []
            if node.args:
                fields += _dict_keys(self._resolve(node.args[0]))
            for a in node.args[1:]:
                d = self._resolve(a)
                for k in _dict_keys(d):
                    if k.startswith("$") and isinstance(d, ast.Dict):
                        for kk, vv in zip(d.keys, d.values):
                            if isinstance(kk, ast.Constant) and kk.value == k:
                                fields += _dict_keys(vv)
                    else:
                        fields.append(k)
            seen = []
            for f in fields:
                if f not in seen:
                    seen.append(f)
            self.emit("write", node, {"store": store, "method": WRITE_METHODS[fn], "fields": seen})
            if node.args:
                self._key_use(node, store, node.args[0])
        if fn == "aggregate" and store and node.args:
            self._lookup(node, store, self._resolve(node.args[0]))
        self.generic_visit(node)

    def _filter(self, node, store, flt):
        """A find filter {field: {"$in": names}} where names came from [x.attr for x in rows]: a join."""
        if not isinstance(flt, ast.Dict):
            return
        for k, v in zip(flt.keys, flt.values):
            if not (isinstance(k, ast.Constant) and isinstance(k.value, str) and isinstance(v, ast.Dict)):
                continue
            for kk, vv in zip(v.keys, v.values):
                if isinstance(kk, ast.Constant) and kk.value == "$in":
                    src = self._resolve(vv)
                    if isinstance(src, ast.ListComp) and isinstance(src.elt, ast.Attribute):
                        attr = src.elt.attr
                        for cls, fields in self.orm_fields.items():
                            if attr in fields:
                                self.emit("join", node, {"left": self.orm_tables[cls], "right": store,
                                                         "keys": {"left": attr, "right": k.value}})
                                break

    def _lookup(self, node, store, pipeline):
        if not isinstance(pipeline, ast.List):
            return
        for stage in pipeline.elts:
            if isinstance(stage, ast.Dict):
                for k, v in zip(stage.keys, stage.values):
                    if isinstance(k, ast.Constant) and k.value == "$lookup" and isinstance(v, ast.Dict):
                        spec = {kk.value: _const_str(vv) for kk, vv in zip(v.keys, v.values) if isinstance(kk, ast.Constant)}
                        if spec.get("from"):
                            self.emit("join", node, {"left": store, "right": spec["from"],
                                                     "keys": {"left": spec.get("localField"), "right": spec.get("foreignField")}})

    def _key_use(self, node, store, arg):
        d = self._resolve(arg)
        keys = _dict_keys(d)
        if keys:
            self.emit("key_use", d if isinstance(arg, ast.Name) else node, {"store": store, "field": keys[0]} if len(keys) == 1 else {"store": store, "field": keys})

    def _sql(self, node, sql: str):
        verb = re.search(r"\b(select|insert|update|delete|create)\b", sql, re.I).group(1).lower()
        tables = [t for _, t in SQL_RE.findall(sql)]
        if verb == "create":
            m = re.search(r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([A-Za-z_][A-Za-z0-9_.]*)", sql, re.I)
            if m:
                self.emit("ddl", node, {"table": m.group(1), "sql": sql.strip()[:200]})
            return
        joins = re.findall(r"JOIN\s+([A-Za-z_][A-Za-z0-9_.]*)\s+(?:AS\s+\w+\s+|\w+\s+)?ON\s+([A-Za-z_][\w.]*)\s*=\s*([A-Za-z_][\w.]*)", sql, re.I)
        for right, a, b in joins:
            self.emit("join", node, {"left": a.split(".")[0] if "." in a else (tables[0] if tables else None), "right": right,
                                     "keys": {"left": a.split(".")[-1], "right": b.split(".")[-1]}})
        for t in dict.fromkeys(tables):
            kind = "read" if verb == "select" else "write"
            self.emit(kind, node, {"store": t, "method": verb, "fields": []})


def first_pass(files: list[tuple[str, str]]) -> tuple[dict, dict]:
    """Collect ORM classes across files so reads through a class resolve to its table."""
    tables, fields = {}, {}
    for rel, src in files:
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                tbl, fl = None, []
                django = any(_name(b) == "Model" for b in node.bases)
                for st in node.body:
                    if isinstance(st, ast.Assign) and isinstance(st.targets[0], ast.Name):
                        if st.targets[0].id == "__tablename__":
                            tbl = _const_str(st.value)
                        elif isinstance(st.value, ast.Call):
                            fn = _name(st.value.func) or ""
                            if fn in ("Column", "mapped_column") or (django and fn.endswith("Field")):
                                fl.append(st.targets[0].id)
                if tbl is None and django and fl:
                    tbl = node.name.lower()
                if tbl and fl:
                    tables[node.name] = tbl
                    fields[node.name] = fl
    return tables, fields


def scan(root: str) -> tuple[list[dict], dict]:
    files, skipped = [], 0
    for dirpath, dirs, names in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS and not d.startswith("."))
        for n in sorted(names):
            path = os.path.join(dirpath, n)
            rel = os.path.relpath(path, root).replace(os.sep, "/")
            if n.endswith(".py"):
                try:
                    with open(path, encoding="utf-8") as f:
                        files.append((rel, f.read()))
                except (OSError, UnicodeDecodeError):
                    skipped += 1
            elif n.endswith(OTHER_LANG):
                skipped += 1
    tables, fields = first_pass(files)
    items = []
    for rel, src in files:
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        fs = FileScan(rel, tables, fields)
        fs.src = src
        fs.visit(tree)
        items.extend(fs.items)
    # relationship cardinality from foreign keys, now that every class is known
    by_class = {it["data"]["class"]: it["data"] for it in items if it["kind"] == "orm_entity"}
    for data in by_class.values():
        for r in data.get("relationships") or []:
            target = by_class.get(r["to"])
            if not target:
                r["kind"] = "unknown"
                continue
            mine_to_target = any(fk["to"].split(".")[0] == target["table"] for fk in data.get("foreign_keys") or [])
            target_to_mine = any(fk["to"].split(".")[0] == data["table"] for fk in target.get("foreign_keys") or [])
            r["kind"] = "many-to-one" if mine_to_target else ("one-to-many" if target_to_mine else "unknown")
    coverage = {"languages": ["python"], "files_scanned": len(files), "files_skipped": {"other_language": skipped}}
    return items, coverage


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=".")
    ap.add_argument("--source", default="src:app")
    ap.add_argument("--data-dir", default="docs/02-design/data")
    ap.add_argument("--environment", default="dev")
    ap.add_argument("--taken-at", help="ISO timestamp (default now)")
    a = ap.parse_args(argv)
    at = parse_ts(a.taken_at)
    items, coverage = scan(a.root)
    doc = envelope("code", a.source, at, "code_adapter.py",
                   {"mode": "offline", "environment": a.environment, "read_only": True}, items, {"coverage": coverage})
    path = write_evidence(a.data_dir, doc, at)
    log_run(a.data_dir, "code_adapter", a.source, "offline", a.environment, True, ["scan"], "ok", at=at)
    set_source_status(a.data_dir, a.source, "extracted")
    print("code_adapter: %d item(s) from %d Python file(s), %d other-language file(s) skipped -> %s"
          % (len(items), coverage["files_scanned"], coverage["files_skipped"]["other_language"], path))
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
