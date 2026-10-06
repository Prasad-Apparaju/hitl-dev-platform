# Graphify knowledge graph (brownfield Step 9)

The commands for Step 9 of `/hitl:dev-start-brownfield` when Graphify is installed. Run them, then return to `SKILL.md` Step 10.

Graphify builds a queryable knowledge graph from your docs and code. HITL skills use it to look up domains, incidents, and test coverage without exhausting the context window.

**If installed:** run the per-project commands now:
```bash
graphify .              # build the graph from existing code and docs
graphify hook install   # auto-rebuild on every git commit
```

Then commit so teammates get it immediately:
```bash
echo "graphify-out/manifest.json" >> .gitignore
echo "graphify-out/cost.json" >> .gitignore
git add graphify-out/ .gitignore
git commit -m "chore: add graphify knowledge graph"
```
