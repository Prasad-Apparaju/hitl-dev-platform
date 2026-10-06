# Migration setup — step detail

Read from Steps 0, 5 and 6 of `/hitl:dev-start-migration`. Each section holds the worked detail
for one step: the files to write, the table to read against, the choices to put to the person.
The rule each step turns on stays in SKILL.md.

## Contents

- Step 0, sub-steps 3 to 7 — project scaffolding
- Step 5 — reading the source code
- Step 5 — source inaccessible
- Step 6 — external documentation options

---

## Step 0, sub-steps 3 to 7 — project scaffolding

Run these after the hook wrappers are written (sub-step 2) and before the "Hooks wired" message
(sub-step 4 in SKILL.md). `$PLUGIN_ROOT` is the plugin path found in sub-step 1.

3. Create `.claude/settings.json` only if it does not already exist:
   ```json
   {
     "statusLine": { "type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/.hitl/hooks/statusline-hitl.sh\"" },
     "hooks": {
       "SessionStart": [{ "hooks": [{ "type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/.hitl/hooks/hitl-gate.sh\"" }] }],
       "UserPromptSubmit": [{ "hooks": [{ "type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/.hitl/hooks/welcome.sh\"" }] }],
       "PreToolUse": [{ "matcher": "Edit|Write", "hooks": [{ "type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/.hitl/hooks/check-hitl-context.sh\"" }, { "type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/.hitl/hooks/first-pass-permissions.sh\"" }] }, { "matcher": "Read|Grep|Glob", "hooks": [{ "type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/.hitl/hooks/first-pass-permissions.sh\"" }] }],
       "PostToolUse": [{ "matcher": "Edit|Write", "hooks": [
         { "type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/.hitl/hooks/check-domain-boundary.sh\"" },
         { "type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/.hitl/hooks/rebuild-graph.sh\"" },
         { "type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/.hitl/hooks/sync-step-to-issue.sh\"" }
       ]}],
       "Stop": [{ "hooks": [{ "type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/.hitl/hooks/write-session-summary.sh\"" }] }]
     },
     "permissions": { "allow": ["Bash(git add *)"],
       "deny": ["Read(./.env)", "Read(./.env.*)", "Read(./**/.env)", "Read(./secrets/**)"] }
   }
   ```

4. Update `.gitignore` so session logs don't end up in the product repo — add the entry if not already present:
   ```bash
   grep -q "docs/session-logs" .gitignore 2>/dev/null || printf '\n# HITL session logs — operational artifacts, not product code\ndocs/session-logs/\n' >> .gitignore
   grep -q "first-pass-choices" .gitignore 2>/dev/null || printf '\n# HITL transient working state — the change file and skip ledger ARE committed\n.hitl/*.tmp\n.hitl/*.migrated\n.hitl/first-pass-choices.json\n.hitl/backups/\n' >> .gitignore
   ```

5. Copy default ADR stubs into `docs/02-design/technical/adrs/` — skip any file that already exists (never overwrite existing ADRs):
   ```bash
   mkdir -p docs/02-design/technical/adrs
   for f in "$PLUGIN_ROOT/shared/templates"/adr-000*.md; do
     dest="docs/02-design/technical/adrs/$(basename "$f")"
     [[ -f "$dest" ]] || cp "$f" "$dest"
   done
   ```
   Then fill in today's date in `adr-0001-hitl-adoption.md` and `adr-0002-documentation-first.md` (replace `[fill in: project start date]` with today's ISO date).

6. Install the First Pass validator (FR-29): the fail-closed skip-ledger validator + its criticality catalog (co-located = the trusted CI source) + the CI gate. Without this the skip ledger is **unenforced** — skips can be recorded on every change and nothing certifies them, which is the exact failure the ledger exists to prevent. Idempotent; skips if the plugin copy is absent.
   ```bash
   if [[ -n "$PLUGIN_ROOT" && -d "$PLUGIN_ROOT/shared/ci/first-pass" ]]; then
     mkdir -p ci/first-pass
     cp "$PLUGIN_ROOT/shared/ci/first-pass/"*.py ci/first-pass/ 2>/dev/null
     [[ -f "$PLUGIN_ROOT/shared/workflows.yaml" ]] && cp "$PLUGIN_ROOT/shared/workflows.yaml" ci/first-pass/workflows.yaml
     if [[ -f "$PLUGIN_ROOT/shared/ci-workflows/first-pass-check.yml" ]]; then
       mkdir -p .github/workflows
       [[ ! -f .github/workflows/first-pass-check.yml ]] && cp "$PLUGIN_ROOT/shared/ci-workflows/first-pass-check.yml" .github/workflows/
     fi
     echo "Skip-record validator installed: ci/first-pass/ (validator + catalog) + .github/workflows/first-pass-check.yml."
   fi
   ```

7. Install the semgrep convention rules — the rule set `/hitl:dev-check-conventions` scans with. Without them that command fails outright (`unable to find a config; path .semgrep does not exist`). Only absent files are copied; `/hitl:dev-update` updates installed rules with a diff.
   ```bash
   [[ -n "$PLUGIN_ROOT" && -f "$PLUGIN_ROOT/shared/semgrep/install.sh" ]] && bash "$PLUGIN_ROOT/shared/semgrep/install.sh"
   ```

---

## Step 5 — reading the source code

For option A or B (the source code is reachable):

1. Read the top-level structure to orient, then focus on:

   | What to extract | Where to look |
   |---|---|
   | Exposed APIs | REST routes, GraphQL schema, gRPC `.proto` files, event topics published |
   | Core domain logic | Services, use cases, domain objects, business rule implementations |
   | Data contracts | DB schema, migration files, ORM models, key data shapes |
   | Integration points | Outbound HTTP clients, queue consumers, webhook handlers, third-party SDKs |
   | Auth and access control | Who can call what — roles, scopes, ownership rules |
   | Background jobs | Scheduled tasks, workers, async processors |

2. Use Graphify if available on the source repo:
   ```
   /graphify query "API endpoints domain services data models integrations auth"
   ```

Then produce the inventory from the template named in SKILL.md and put the completeness question to the person.

---

## Step 5 — source inaccessible

For option C:

**If C — source is inaccessible:**

Ask: "Describe the source system's key APIs, core business behaviors, data contracts, and integration points. I'll structure them as the behavioral inventory."

Record what the user provides. Mark every entry `confidence: low — from description only`. Say: "The behavioral inventory is based on your description since the source code isn't available. Treat it as a starting point — expand it whenever a gap is discovered during development."

Write `docs/00-migration/source-behavioral-inventory.md` with entries marked `confidence: low`.

---

## Step 6 — external documentation options

Present the following choice to the user:

---
**Step 6 is optional — choose one:**

**A — Copy docs into this repo** (`docs/00-migration/external-reference/`)
> Best when: the reference repo is private, may become unavailable, or team members lack access.
> What happens: you provide file paths or paste content; I copy them as-is. No editing.
> Downside: files can drift from the source of truth over time.

**B — Link only (skip copy)**
> Best when: the reference repo is public and key decisions are already captured in `system-manifest.yaml` and `migration-context.yaml` (which Steps 3–4 produce).
> What happens: I verify the `poc_reference` links in `migration-context.yaml` are live and confirm key architectural decisions are reflected in the manifest. No file copy.
> Downside: future sessions need network access to the reference repo.

**C — No external docs**
> The architect will design from scratch using the migration context collected in Step 1.

---

**If A:** For each external document, ask the user to provide the file path or paste the content. Copy or save to `docs/00-migration/external-reference/<doc-name>.<ext>`. Do NOT edit the external docs — preserve them exactly as received. Then print the staged file list.

**If B:** Verify `poc_reference.repo` in `migration-context.yaml` is reachable (`curl -sI <url> | head -1` or `gh repo view <repo>`). Confirm key decisions are present in `system-manifest.yaml` (check `key_decisions` block or `robustness_primitives`). Report: "Reference links verified. Key decisions captured in manifest. No file copy needed." and move on.

**If C:** Say "No external docs to ingest — the architect will design from scratch." and move on.
