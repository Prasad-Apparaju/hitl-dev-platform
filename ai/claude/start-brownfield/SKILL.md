---
description: Onboard an existing codebase into the HITL process. Generates a documentation baseline from existing code, seeds the test and incident registries, and prepares for docs-first development going forward.
argument-hint: "[optional: path to source root or description of the codebase]"
disable-model-invocation: true
---

# Onboard an Existing Codebase

Bringing an existing codebase into HITL AI-Driven Development. Work through these steps in order — pause after each and wait for confirmation before proceeding.

**Quick sanity check:** If this is a brand-new project with no source code, use `/hitl:dev-start-from-prd` instead. If you are migrating from one system to another (not just onboarding what exists), use `/hitl:dev-start-migration`.

---

## Step 0 — Wire up HITL hooks (once per project)

Check whether `.hitl/hooks/` already exists.

**If it does — hooks are already wired. Skip sub-steps 1–3, but still run sub-steps 4–5** (gitignore and ADR stubs are idempotent and must always be present):

1. Find the plugin root (needed for the ADR copy):
   ```bash
   python3 -c "
   import json, os, sys
   try:
       d = json.load(open(os.path.expanduser('~/.claude/plugins/installed_plugins.json')))
       for inst in d.get('plugins', {}).get('hitl@hitl', []):
           p = inst.get('installPath', '')
           if os.path.isfile(os.path.join(p, '.claude-plugin/plugin.json')):
               print(p); sys.exit(0)
   except: pass
   try:
       d = json.load(open(os.path.expanduser('~/.claude/settings.json')))
       for p in d.get('plugins', []):
           path = p if isinstance(p, str) else p.get('path', '')
           if os.path.isfile(os.path.join(path, '.claude-plugin/plugin.json')):
               print(path); sys.exit(0)
   except: pass
   print('NOT_FOUND')
   "
   ```
2. Run sub-steps 4 and 5 below (gitignore + ADR stubs), then say "Hooks already wired — skipped hook creation, ensured ADR stubs present." and proceed to Step 1.

**If it does not exist — run all sub-steps:**

1. Find the HITL plugin path:
   ```bash
   python3 -c "
   import json, os, sys
   try:
       d = json.load(open(os.path.expanduser('~/.claude/plugins/installed_plugins.json')))
       for inst in d.get('plugins', {}).get('hitl@hitl', []):
           p = inst.get('installPath', '')
           if os.path.isfile(os.path.join(p, '.claude-plugin/plugin.json')):
               print(p); sys.exit(0)
   except: pass
   try:
       d = json.load(open(os.path.expanduser('~/.claude/settings.json')))
       for p in d.get('plugins', []):
           path = p if isinstance(p, str) else p.get('path', '')
           if os.path.isfile(os.path.join(path, '.claude-plugin/plugin.json')):
               print(path); sys.exit(0)
   except: pass
   print('NOT_FOUND')
   "
   ```
   If the result is `NOT_FOUND`, stop and say: "The HITL plugin was not found in your Claude Code settings. Install it with: `claude plugin marketplace add pappar/hitl-claude-plugin && claude plugin install hitl@hitl`"

2. Create `.hitl/hooks/` and write a wrapper for each of these nine hooks: `welcome`, `hitl-gate`, `check-hitl-context`, `first-pass-permissions`, `check-domain-boundary`, `rebuild-graph`, `write-session-summary`, `sync-step-to-issue`, `statusline-hitl`. (The shared `_steps.sh` library is sourced by the renderers from the plugin directly — it does not need a wrapper.) Each wrapper discovers the plugin path at runtime — surviving plugin updates, reinstalls and version bumps. **Use the wrapper body from Step 0 of [`/hitl:dev-start-from-prd`](../start-from-prd/SKILL.md) verbatim; it is the single definition.** It resolves a working interpreter before use (on Windows `python3` is the Microsoft Store stub — on PATH, runs nothing), exports `HITL_PY`/`PYTHONUTF8` so hooks do not re-probe or crash on the breadcrumb glyphs, then execs the real hook from the plugin. Copying it into this skill is how it drifted before: three copies, two of them stale, shipping hooks that silently no-op.
   Replace `<name>` with the hook name for each file. Run `chmod 750` on each file.

3. Create `.claude/settings.json` only if it does not already exist:
   ```json
   {
     "statusLine": { "type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/.hitl/hooks/statusline-hitl.sh\"" },
     "hooks": {
       "SessionStart": [{ "hooks": [{ "type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/.hitl/hooks/hitl-gate.sh\"" }] }],
       "UserPromptSubmit": [{ "hooks": [{ "type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/.hitl/hooks/welcome.sh\"" }] }],
       "PreToolUse": [{ "matcher": "Edit|Write", "hooks": [
         { "type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/.hitl/hooks/check-hitl-context.sh\"" },
         { "type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/.hitl/hooks/first-pass-permissions.sh\"" }
       ]}, { "matcher": "Read|Grep|Glob", "hooks": [{ "type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/.hitl/hooks/first-pass-permissions.sh\"" }] }],
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
   # `.hitl/` itself is COMMITTED — current-change.yaml is the handoff record and the first-pass CI
   # gate reads it from the checkout. Only transient working files are ignored (note `.hitl/backups/`
   # is where ops-backup-database writes database dumps).
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

6. Say: "Hooks wired. `.hitl/hooks/`, `.claude/settings.json`, `.gitignore`, and 8 baseline ADRs created in `docs/02-design/technical/adrs/`. **Restart Claude Code now** so the hooks load, then re-run this command to continue setup."

---

## Step 1 — Map the codebase

**Write `.hitl/current-change.yaml` now** (enables breadcrumbs immediately) with the embedded
`brownfield` workflow block — copied from the catalog at `ai/shared/workflows.yaml`:
```yaml
schema_version: "2.0"
change_id: brownfield-setup
tier: 0
status: planning
workflow:
  id: brownfield
  total: 11
  steps:
    - { n: 1,  key: map_code,        label: "MapCode",    phase: "Brownfield Setup", status: current }
    - { n: 2,  key: claude_md,       label: "CLAUDE.md",  phase: "Brownfield Setup", status: open }
    - { n: 3,  key: manifest,        label: "Manifest",   phase: "Brownfield Setup", status: open }
    - { n: 4,  key: arch_review,     label: "ArchRvw",    phase: "Brownfield Setup", status: open }
    - { n: 5,  key: verify_pipeline, label: "Pipeline",   phase: "Brownfield Setup", status: open }
    - { n: 6,  key: observability,   label: "Observ",     phase: "Brownfield Setup", status: open }
    - { n: 7,  key: priority_docs,   label: "Docs",       phase: "Brownfield Setup", status: open }
    - { n: 8,  key: seed_registries, label: "Registries", phase: "Brownfield Setup", status: open }
    - { n: 9,  key: graphify,        label: "Graphify",   phase: "Brownfield Setup", status: open }
    - { n: 10, key: create_issue,    label: "Issue",      phase: "Brownfield Setup", status: open }
    - { n: 11, key: confirm_ready,   label: "Ready",      phase: "Brownfield Setup", status: open }
current_step:
  number: 1
  name: "Map codebase"
  phase: "Brownfield Setup"
```

> **Breadcrumb advancement:** at the start of each step below, edit `.hitl/current-change.yaml`
> to set the previous step's `status: done` and the current step's `status: current`, and update
> `current_step` to match.

List the top-level directories and identify source code locations.
- Ask: "Are these the right source directories? Anything to exclude?"
- Confirm the language and framework.

---

## Step 2 — Customize CLAUDE.md

Update `.hitl/current-change.yaml` — set `current_step`:
```yaml
  number: 2
  name: "Customize CLAUDE.md"
  phase: "Brownfield Setup"
```

If `CLAUDE.md` has template placeholders (`{{coding_standards}}`, `{{#conventions}}`):
- Ask: "What are this project's naming conventions, test framework, and any standards AI should follow?"
- Fill in the placeholders based on their answers and the observed codebase patterns.
- Show a diff of what changed.
- Ask: "Does this look right? Any other conventions to add?"

If `CLAUDE.md` already has real content, say: "`CLAUDE.md` looks customized — skipping." and move on.

---

## Step 3 — Generate the system manifest baseline

Update `.hitl/current-change.yaml` — set `current_step`:
```yaml
  number: 3
  name: "Generate manifest"
  phase: "Brownfield Setup"
```

If `docs/system-manifest.yaml` is missing or template-only:
- Run: `python tools/generate-manifest/generator.py --source [confirmed source dirs] --output docs/system-manifest.yaml`
- If the generator is unavailable, say so and ask: "Describe your main services and domains — I'll create the manifest manually."
- After generating, show the domain list and ask: "Review these domains. What should be added, removed, or renamed?"
- Incorporate feedback and update the manifest.

If a real manifest already exists, read it, summarize the domains, and ask: "Is this manifest still accurate? Anything outdated?"

**Install the manifest drift checker.** The manifest is only load-bearing if something keeps it honest. Resolve the plugin root once (reused in later steps), then copy the checker into the repo so `/hitl:dev-check-conventions` and the `ci/workflows/*.yml` templates (which reference it by repo path) can run it:

```bash
PLUGIN_ROOT=$(python3 -c "import json,os,sys;d=json.load(open(os.path.expanduser('~/.claude/plugins/installed_plugins.json')));[print(i['installPath']) or sys.exit(0) for i in d.get('plugins',{}).get('hitl@hitl',[]) if os.path.isfile(os.path.join(i.get('installPath',''),'.claude-plugin/plugin.json'))]" 2>/dev/null)
if [[ -n "$PLUGIN_ROOT" && -f "$PLUGIN_ROOT/shared/ci/manifest-drift/check_manifest_drift.py" ]]; then
  mkdir -p ci/manifest-drift
  [[ ! -f ci/manifest-drift/check_manifest_drift.py ]] && cp "$PLUGIN_ROOT/shared/ci/manifest-drift/"*.py ci/manifest-drift/
fi
# First Pass (FR-29): validator + its criticality catalog (co-located = the trusted CI source) + CI gate.
if [[ -n "$PLUGIN_ROOT" && -d "$PLUGIN_ROOT/shared/ci/first-pass" ]]; then
  mkdir -p ci/first-pass
  cp "$PLUGIN_ROOT/shared/ci/first-pass/"*.py ci/first-pass/ 2>/dev/null
  [[ -f "$PLUGIN_ROOT/shared/workflows.yaml" ]] && cp "$PLUGIN_ROOT/shared/workflows.yaml" ci/first-pass/workflows.yaml
  if [[ -f "$PLUGIN_ROOT/shared/ci-workflows/first-pass-check.yml" ]]; then
    mkdir -p .github/workflows
    [[ ! -f .github/workflows/first-pass-check.yml ]] && cp "$PLUGIN_ROOT/shared/ci-workflows/first-pass-check.yml" .github/workflows/
  fi
fi
# Compound-agentic surface (#10): validator + posture-view generator; preserve the repo's manifest-waivers.yaml.
if [[ -n "$PLUGIN_ROOT" && -d "$PLUGIN_ROOT/shared/ci/manifest-agentic" ]]; then
  mkdir -p ci/manifest-agentic tools/manifest-agentic
  cp "$PLUGIN_ROOT/shared/ci/manifest-agentic/"*.py ci/manifest-agentic/ 2>/dev/null
  [[ ! -f ci/manifest-agentic/manifest-waivers.yaml && -f "$PLUGIN_ROOT/shared/ci/manifest-agentic/manifest-waivers.yaml" ]] && cp "$PLUGIN_ROOT/shared/ci/manifest-agentic/manifest-waivers.yaml" ci/manifest-agentic/
  cp "$PLUGIN_ROOT/shared/tools/manifest-agentic/"*.py tools/manifest-agentic/ 2>/dev/null
fi

# Semgrep convention rules (issue #47): the rule set /hitl:dev-check-conventions scans with.
# Installs only what is absent — .semgrep/ is co-owned; /hitl:dev-update updates it with a diff.
[[ -n "$PLUGIN_ROOT" && -f "$PLUGIN_ROOT/shared/semgrep/install.sh" ]] && bash "$PLUGIN_ROOT/shared/semgrep/install.sh"
```

The checker derives its scan roots from the manifest's listed files, so it needs no per-project configuration. If `$PLUGIN_ROOT` is empty, skip; `/hitl:dev-check-conventions` reports the checker as absent rather than passing.

---

## Step 4 — Review existing architecture

Update `.hitl/current-change.yaml` — set `current_step`:
```yaml
  number: 4
  name: "Arch review"
  phase: "Brownfield Setup"
```

Run `/hitl:architect-review-existing` to reconstruct the architectural decisions already in the codebase, interview the architect to confirm rationale and constraints, and document them as real ADRs before any incremental work begins.

This step produces:
- A tech stack summary
- ADR-0005+ for significant existing decisions (framework, data, auth, API style, deployment, test strategy)
- A list of architectural concerns that affect HITL compliance or first-change risk

Do not proceed to Step 7 until the architect has confirmed the ADRs are accurate.

---

## Step 5 — Verify build and deployment pipeline

Update `.hitl/current-change.yaml` — set `current_step`:
```yaml
  number: 5
  name: "Verify pipeline"
  phase: "Brownfield Setup"
```

The deployment view generated in Step 4 (Phase 4c of `/hitl:architect-review-existing`) describes the CI/CD pipeline. This step confirms it actually works before feature development begins.

**1. Identify the CI/CD system:**

Check which CI/CD configuration files exist:

| File | System |
|---|---|
| `.github/workflows/*.yml` | GitHub Actions |
| `Jenkinsfile` | Jenkins |
| `.gitlab-ci.yml` | GitLab CI |
| `.circleci/config.yml` | CircleCI |
| `.buildkite/pipeline.yml` | Buildkite |

If none found: skip to "Pipeline missing" below.

**2. Verify the build:**

Run the project's build command (infer from the tech stack confirmed in Step 2 — `npm run build`, `mvn package`, `go build ./...`, `./gradlew build`, etc.).

- ✅ Build passes → continue
- 🔴 Build fails → record the error and say: "Build is broken — fix this before feature work begins. Run `/hitl:ops-build` for a structured diagnosis."

**3. Verify the deployment path:**

Check whether the CI/CD config includes:
- A job that deploys to at least one non-production environment (staging, dev, test)
- A job or manual gate for production deploy

The 31-step workflow (`/hitl:dev-practices`) gates every PR on a passing staging deploy — if no staging job exists, that gate cannot function.

- ✅ Staging deploy job exists → proceed
- 🟡 No staging deploy job → note it: "The HITL staging gate will need a manual workaround until a staging deploy job is added."
- 🔴 No deploy jobs at all → treat same as pipeline missing below

**Pipeline missing or broken:**

If no CI/CD config exists, or the build fails and cannot be quickly fixed, say:

> "No working build pipeline found. This is a 🔴 concern — the 31-step workflow requires a passing build and a staging deploy path before a PR can be closed. Options:
> - Scaffold a CI/CD config now: describe your hosting target (GitHub Actions → AWS/GCP/Azure/Railway/Fly.io) and I'll generate a starter pipeline
> - Set it up manually and re-run this step when ready
> - Proceed and accept that the build and deploy steps of the 31-step workflow will need manual execution until the pipeline exists"

If they want a scaffold, generate a minimal CI/CD config (build → test → deploy-to-staging) using the tech stack from Step 2 and the deployment target from the deployment view. Do not include a production deploy job without an explicit approval gate.

**Persist the verdicts (required):** copy `"$PLUGIN_ROOT/shared/templates/platform-readiness-template.yaml"`
to `docs/04-operations/platform-readiness.yaml` if missing, set `project_kind: brownfield`,
and record this step's verdicts there: `E1` (build reproducible), `E3` (staging deploy from
CI), `D1` (suites run in CI and can fail) — evidence rules are in the template header. The
register feeds `/hitl:ops-plan-platform` (Step 11) and the production-deploy gate; a verdict
not written here does not exist.

---

## Step 6 — Set up observability

Update `.hitl/current-change.yaml` — set `current_step`:
```yaml
  number: 6
  name: "Set up observability"
  phase: "Brownfield Setup"
```

HITL requires two observability layers: **application observability** (logs, metrics, tracing,
alerting) and **agentic observability** (session logs, token cost). Both must be in place before
the first Tier 2 change is deployed.

**Read [observability-survey.md](observability-survey.md) and perform every step in it** — the
signal-by-signal survey, the severity table, and the required `F1` record in the readiness
register. An unrecorded gap is invisible to the roadmap and the deploy gate.


---

## Step 7 — Identify priority components for documentation

Update `.hitl/current-change.yaml` — set `current_step`:
```yaml
  number: 7
  name: "Priority docs"
  phase: "Brownfield Setup"
```

Ask: "Which components are most critical and most likely to change in the near term? List up to three."

For each component:
- Say: "I'll generate an HLD and LLD for [component]. Run `/hitl:dev-generate-docs` or I can do it now — which do you prefer?"
- If they want it now, run `/hitl:dev-generate-docs` for that component.
- Note: this is incremental — you do not need to document everything before starting work.

---

## Step 8 — Seed the registries

Update `.hitl/current-change.yaml` — set `current_step`:
```yaml
  number: 8
  name: "Seed registries"
  phase: "Brownfield Setup"
```

The 31-step workflow queries these two registries at multiple points. They must exist before `/hitl:dev-practices` is run for the first time.

**Test registry** (`docs/03-engineering/testing/test-registry.yaml`):
- Ask: "Do you have existing tests? If so, I'll create a registry stub from your test files."
- If yes: scan `tests/`, `spec/`, or equivalent; generate one entry per test file with `domain` and `path`. Leave `risk` and `covers` as DRAFT.
- If no: create an empty stub.

**Incident registry** (`docs/04-operations/incident-registry.yaml`):
- Ask: "What broke in production in the last 6 months? Describe each incident in one sentence."
- For each answer, add one entry with `description`, `domain` (best guess), and `date`.
- If they have nothing: create an empty stub and say: "You can add entries later — after each production incident, run `/hitl:ops-incident`."

**Product baseline** (`docs/01-product/prd.md`): the PM and QA skills read the PRD for personas and requirements, so a brownfield project with no PRD leaves them nowhere to land. Initialize the PRD *shell*, not a retroactive spec of existing behaviour (that lives in the reverse-engineered technical docs), only personas and format so the next requirement has a home. If `docs/01-product/prd.md` is missing and `$PLUGIN_ROOT` (Step 3) is set, run `mkdir -p docs/01-product && cp "$PLUGIN_ROOT/shared/templates/prd-template.md" docs/01-product/prd.md`. Then ask "Who are the primary users of this system, and what does each need?" and fill §3 (Target Users and Personas); leave §5 (Functional Requirements) empty, noted "No requirements yet — added via `/hitl:pm-add-feature`." Say: "Product baseline initialized; PM and QA skills are now active."

---

## Step 9 — Build Graphify knowledge graph (optional)

Update `.hitl/current-change.yaml` — set `current_step`:
```yaml
  number: 9
  name: "Graphify"
  phase: "Brownfield Setup"
```

Graphify builds a queryable knowledge graph from your docs and code. HITL skills use it to look up domains, incidents, and test coverage without exhausting the context window.

Run `graphify --version` to check if it is installed.

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

**If not installed:** say "Graphify not found — skipping. Install it when convenient with `uv tool install graphifyy && graphify claude install`, then run `graphify .` in this repo. HITL skills fall back gracefully without it. See `shared/graphify-setup.md`." and continue to Step 8.

---

## Step 10 — Create your first change issue

Update `.hitl/current-change.yaml` — set `current_step`:
```yaml
  number: 10
  name: "Create issue"
  phase: "Brownfield Setup"
```

Ask: "What's the first change you want to make now that this project is onboarded?"
- Run: `gh issue create --title "[change description]" --body "First tracked change after HITL brownfield onboarding."`
- Show the issue URL.

---

## Step 11 — Confirm ready

Update `.hitl/current-change.yaml` — set `current_step`:
```yaml
  number: 11
  name: "Confirm ready"
  phase: "Brownfield Setup"
```

**Before the closing message, exclude persona profiles from git.** `.hitl/people/` holds
descriptions of named colleagues. Committed, they land in PR diffs and stay in history after
deletion. `init-project.sh` adds this rule and a plugin-installed team never runs that script, so
it has to happen here.

```bash
GITIGNORE=".gitignore"
if ! grep -q "^\.hitl/people/" "$GITIGNORE" 2>/dev/null; then
  printf '\n# HITL persona profiles — descriptions of people. Local unless your team decides otherwise.\n.hitl/people/\n' >> "$GITIGNORE"
fi
git check-ignore -q .hitl/people/ 2>/dev/null \
  && echo "✓ .gitignore — .hitl/people/ excluded" \
  || echo "COULD NOT exclude .hitl/people/ — say so before any profile is written here."
```

Output this exactly:

---
**Brownfield baseline established.**

You are starting incrementally: manifest and priority component docs exist, registries are seeded.

**What this means for your first changes:**
- Treat AI output from steps 5, 10, and 14 as drafts — the docs are new and may not yet reflect actual behavior. Increase human review scrutiny until the docs have been corrected through real use.
- If `/hitl:dev-practices` stops with "no LLD found" on an undocumented component, run `/hitl:dev-generate-docs` for that component, then resume. This friction decreases naturally as each component gets its first doc pass through real use.

For every change going forward:
1. Create a GitHub issue — or use `/hitl:pm-add-feature` / `/hitl:pm-design-feature` to shape requirements first
2. Run `/hitl:dev-practices` — the 31-step workflow starts here
3. Update HLD/LLD if the design changes
4. Code → tests → PR

**Next: the platform roadmap.** Steps 5-6 wrote the readiness register; changes can be
*made* now but *delivered to customers* only once it is green. Run
`/hitl:ops-plan-platform roadmap` to turn the recorded gaps into phased GitHub issues (each
an ordinary HITL change). Tier 2+ **production** deploys stay blocked until delivery-ready.

---
