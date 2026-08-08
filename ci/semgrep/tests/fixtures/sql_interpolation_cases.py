"""Fixture for the sql-injection rule regression test (issue #45). NOT executable code.

Every SQL-interpolation shape the rules are meant to catch, plus controls that must stay clean.
Lives under tests/fixtures/ so `.semgrep/.semgrepignore` keeps the deliberate violations out of
the repo-wide convention scan.

Line numbers are asserted by ci/semgrep/test_sql_injection_rule.py — if you edit this file,
update EXPECTED there. Keep one case per marked line.
"""

FRAG = "SELECT 1"

# ── must be FLAGGED: execute() ────────────────────────────────────────────────────────────

op.execute(f"DELETE FROM t USING ({FRAG}) s")  # BAD: single-line f-string

op.execute(f"""DELETE FROM t USING ({FRAG}) s""")  # BAD: triple-quoted f-string

# BAD: implicit concatenation, f-string first — the shape that slipped past before #45
op.execute(f"DELETE FROM t USING ({FRAG}) s" " WHERE a.id = s.id")

# BAD: implicit concatenation, plain string first
op.execute("DELETE FROM t" f" USING ({FRAG}) s")

op.execute("DELETE FROM t USING (" + FRAG + ") s")  # BAD: explicit concatenation

op.execute("DELETE FROM t USING ({}) s".format(FRAG))  # BAD: .format()

# ── must be FLAGGED: text() ───────────────────────────────────────────────────────────────

text(f"SELECT {FRAG}")  # BAD: f-string in text()

text(f"SELECT {FRAG}" " WHERE 1=1")  # BAD: implicit concatenation in text()

text("SELECT " f"{FRAG}")  # BAD: implicit concatenation, plain first

# ── must stay CLEAN: no interpolation ─────────────────────────────────────────────────────

op.execute("DELETE FROM t USING (SELECT 1) s")  # OK: plain literal

op.execute("DELETE FROM t" " USING (SELECT 1) s")  # OK: concatenation of plain literals

text("SELECT * FROM t WHERE id = :id").bindparams(id=1)  # OK: bound parameter
