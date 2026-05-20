# Graphify Setup

Graphify turns your project's code, docs, and schemas into a queryable knowledge graph that your AI assistant reads instead of re-scanning files. In the HITL workflow, skills use `/graphify query "..."` to find domain boundaries, incidents, and test coverage without hitting the context window limit.

**GitHub:** https://github.com/safishamsi/graphify  
**PyPI package:** `graphifyy` (double-y — the CLI command is still `graphify`)

---

## One-time install (per machine)

```bash
# Recommended — puts graphify on PATH automatically
uv tool install graphifyy

# Alternatives
pipx install graphifyy
pip install graphifyy        # add ~/.local/bin (Linux) or ~/Library/Python/3.x/bin (Mac) to PATH
```

**Prerequisites:** Python 3.10+, and `uv` or `pipx` (either handles PATH automatically).

```bash
# macOS quick install
brew install python@3.12 uv

# Ubuntu/Debian
sudo apt install python3.12 pipx
# or: curl -LsSf https://astral.sh/uv/install.sh | sh
```

---

## Per-project setup (run once per repo)

**Step 1 — Register the `/graphify` skill with Claude Code:**
```bash
graphify claude install
```
This writes the hook and skill config that makes `/graphify` available inside Claude Code sessions.

**Step 2 — Build the initial graph:**
```bash
graphify .
```
This produces three files in `graphify-out/`:
- `graph.json` — the full knowledge graph; queried by HITL skills
- `graph.html` — visual explorer; open in any browser
- `GRAPH_REPORT.md` — key concepts, surprising connections, suggested questions

**Step 3 — Install the git commit hook (incremental rebuild):**
```bash
graphify hook install
```
After this, every `git commit` automatically re-extracts changed AST nodes — no API cost, no manual rebuild needed.

**Step 4 — Commit `graphify-out/` to git:**
```bash
# Add to .gitignore first:
echo "graphify-out/manifest.json" >> .gitignore
echo "graphify-out/cost.json" >> .gitignore

git add graphify-out/
git commit -m "chore: add initial graphify knowledge graph"
```
Committing the graph means every teammate starts with a working map — no rebuild required after `git pull`.

---

## Keeping the graph current

| Situation | Command |
|---|---|
| Docs changed, re-extract those nodes | `graphify . --update` |
| Rebuild clustering only (no API cost) | `graphify . --cluster-only` |
| Skip HTML output (CI/headless) | `graphify . --no-viz` |
| Full rebuild from scratch | `graphify .` |

The Claude Code PostToolUse hook in this project (`hooks/rebuild-graph.sh`) automatically runs `graphify . --update --no-viz` after any write to `docs/` during a session.

---

## Querying the graph

Inside Claude Code, use `/graphify query` for targeted lookups:
```
/graphify query "all domains and facade APIs"
/graphify query "past incidents affecting domain: payments"
/graphify query "test coverage for domain: auth"
/graphify query "services reading or writing table: users"
```

From the terminal:
```bash
graphify query "what connects auth to the database?"
graphify explain "PaymentService"
graphify path "UserService" "DatabasePool"
```

---

## Excluding files

Create `.graphifyignore` in the project root (same syntax as `.gitignore`):
```
node_modules/
dist/
*.generated.py
graphify-out/
```

---

## Availability check

HITL skills check graph availability before running queries:
```bash
ls graphify-out/graph.json 2>/dev/null && echo "available" || echo "unavailable"
```
If `graph.json` is missing, run `graphify .` to build the graph, then re-run the skill.

---

## When Graphify is not required

Projects with fewer than 4 domains and small doc sets fit in the context window — Graphify is optional. Skills always fall back to direct file reads when the graph is unavailable. For larger projects, Graphify is strongly recommended: HITL skills make 10–30 graph queries per session, and direct reads at that volume will exhaust the context window.
