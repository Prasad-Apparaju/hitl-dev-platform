---
description: Onboard an existing codebase into the HITL process. Generates a documentation baseline from existing code, seeds the test and incident registries, and prepares for docs-first development going forward.
argument-hint: "[optional: path to source root or description of the codebase]"
disable-model-invocation: true
---

# Onboard an Existing Codebase

Bringing an existing codebase into HITL AI-Driven Development. Work through these steps in order — pause after each and wait for confirmation before proceeding.

**Quick sanity check:** If this is a brand-new project with no source code, use `/hitl:dev-start-from-prd` instead. If you are migrating from one system to another (not just onboarding what exists), use `/hitl:dev-start-migration`.

## Rules that hold throughout

- **Breadcrumb.** Step 1 writes `.hitl/current-change.yaml`. At the start of every later step, set the previous step's `status: done`, the new step's `status: current`, and `current_step` to the step's `number` and `name` with `phase: "Brownfield Setup"`.
- **Install only what is absent**: never overwrite an existing ADR, `.claude/settings.json`, a waiver file or a CI workflow file. The `.gitignore` edits always run.
- **One wrapper definition**, in Step 0 of `/hitl:dev-start-from-prd`, used verbatim; never copy it into this skill.
- **Shell state does not persist between tool calls.** A fence that needs `$PLUGIN_ROOT` resolves it itself; if it is empty, skip that copy and say so.
- **A verdict not written to `docs/04-operations/platform-readiness.yaml` does not exist.**
- **Reference files** carry the full procedure for Steps 5, 6, 8 and 9; read the one a step names and perform every part of it.

## Step 0 — Wire up HITL hooks (once per project)

Check whether `.hitl/hooks/` already exists.

**If it does:** run sub-step 1 (the ADR copy needs the plugin root), then 4 and 5, then say "Hooks already wired — skipped hook creation, ensured ADR stubs present." and proceed to Step 1.

**If it does not exist, run all sub-steps:**

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

2. Create `.hitl/hooks/` and write a wrapper for each of these nine hooks: `welcome`, `hitl-gate`, `check-hitl-context`, `first-pass-permissions`, `check-domain-boundary`, `rebuild-graph`, `write-session-summary`, `sync-step-to-issue`, `statusline-hitl`. (The shared `_steps.sh` library is sourced by the renderers from the plugin directly — it does not need a wrapper.) **Use the wrapper body from Step 0 of [`/hitl:dev-start-from-prd`](../start-from-prd/SKILL.md) verbatim; it is the single definition.**
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
   grep -q "^\.hitl/linked/" .gitignore 2>/dev/null || printf '.hitl/linked/\n' >> .gitignore   # pinned designs from other repositories (FR-30)
   # `.hitl/` itself is COMMITTED (current-change.yaml is the handoff record the CI gate reads); only transient working files are ignored.
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

## Step 1 — Map the codebase

**Write `.hitl/current-change.yaml` now** (enables breadcrumbs immediately) with the embedded `brownfield` workflow block — copied from the catalog at `ai/shared/workflows.yaml`:
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

List the top-level directories and identify source code locations.
- Ask: "Are these the right source directories? Anything to exclude?"
- Confirm the language and framework.

## Step 2 — Customize CLAUDE.md

Breadcrumb: `number: 2`, `name: "Customize CLAUDE.md"`.

If `CLAUDE.md` has template placeholders (`{{coding_standards}}`, `{{#conventions}}`):
- Ask: "What are this project's naming conventions, test framework, and any standards AI should follow?"
- Fill in the placeholders based on their answers and the observed codebase patterns.
- Show a diff of what changed.
- Ask: "Does this look right? Any other conventions to add?"

If `CLAUDE.md` already has real content, say: "`CLAUDE.md` looks customized — skipping." and move on.

## Step 3 — Generate the system manifest baseline

Breadcrumb: `number: 3`, `name: "Generate manifest"`.

If `docs/system-manifest.yaml` is missing or template-only:
- Run: `python tools/generate-manifest/generator.py --source [confirmed source dirs] --output docs/system-manifest.yaml`
- If the generator is unavailable, say so and ask: "Describe your main services and domains — I'll create the manifest manually."
- After generating, show the domain list and ask: "Review these domains. What should be added, removed, or renamed?"
- Incorporate feedback and update the manifest.

If a real manifest already exists, read it, summarize the domains, and ask: "Is this manifest still accurate? Anything outdated?"

**Install the shipped validators**, which `/hitl:dev-check-conventions` and the `ci/workflows/*.yml` templates run by repo path:

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
# Linked changes (FR-30): the partner-state checker. Data layer (FR-31): validator, scorecard, schema, adapters; the waiver file and the CI template once. Test scenarios (FR-36): the two-way scenario check; its CI template once.
[[ -n "$PLUGIN_ROOT" && -d "$PLUGIN_ROOT/shared/ci/linked" ]] && { mkdir -p ci/linked && cp "$PLUGIN_ROOT/shared/ci/linked/"*.py ci/linked/ 2>/dev/null; }
[[ -n "$PLUGIN_ROOT" && -d "$PLUGIN_ROOT/shared/ci/test-scenarios" ]] && { mkdir -p ci/test-scenarios .github/workflows && cp "$PLUGIN_ROOT/shared/ci/test-scenarios/"*.py ci/test-scenarios/ 2>/dev/null; [[ ! -f .github/workflows/test-scenarios-check.yml ]] && cp "$PLUGIN_ROOT/shared/ci-workflows/test-scenarios-check.yml" .github/workflows/ 2>/dev/null; }
if [[ -n "$PLUGIN_ROOT" && -d "$PLUGIN_ROOT/shared/ci/data-layer" ]]; then
  mkdir -p ci/data-layer tools/data-layer .github/workflows
  cp "$PLUGIN_ROOT/shared/ci/data-layer/"*.py "$PLUGIN_ROOT/shared/ci/data-layer/data-layer.schema.yaml" ci/data-layer/ 2>/dev/null
  cp "$PLUGIN_ROOT/shared/tools/data-layer/"*.py tools/data-layer/ 2>/dev/null
  [[ ! -f ci/data-layer/data-layer-waivers.yaml ]] && cp "$PLUGIN_ROOT/shared/ci/data-layer/data-layer-waivers.yaml" ci/data-layer/ 2>/dev/null
  [[ ! -f .github/workflows/data-layer-check.yml ]] && cp "$PLUGIN_ROOT/shared/ci-workflows/data-layer-check.yml" .github/workflows/ 2>/dev/null
fi

# Semgrep convention rules (issue #47): the rule set /hitl:dev-check-conventions scans with.
# Installs only what is absent — .semgrep/ is co-owned; /hitl:dev-update updates it with a diff.
[[ -n "$PLUGIN_ROOT" && -f "$PLUGIN_ROOT/shared/semgrep/install.sh" ]] && bash "$PLUGIN_ROOT/shared/semgrep/install.sh"
```

The drift checker needs no per-project configuration. If `$PLUGIN_ROOT` is empty, skip; `/hitl:dev-check-conventions` reports the checker as absent rather than passing.

## Step 4 — Review existing architecture

Breadcrumb: `number: 4`, `name: "Arch review"`.

Follow `/hitl:architect-review-existing` from its file (`skills/architect-review-existing/SKILL.md` under the plugin root) to reconstruct the architectural decisions already in the codebase, interview the architect to confirm rationale and constraints, and document them as real ADRs before any incremental work begins.

This step produces:
- A tech stack summary
- ADR-0005+ for significant existing decisions (framework, data, auth, API style, deployment, test strategy)
- A list of architectural concerns that affect HITL compliance or first-change risk

Do not proceed to Step 7 until the architect has confirmed the ADRs are accurate.

## Step 5 — Verify build and deployment pipeline

Breadcrumb: `number: 5`, `name: "Verify pipeline"`.

The deployment view generated in Step 4 (Phase 4c of `/hitl:architect-review-existing`) describes the CI/CD pipeline. This step confirms it actually works before feature development begins.

**Read [pipeline-verification.md](pipeline-verification.md) and perform every part of it**: identify the CI/CD system, run the build, check the deploy path, put the three options to the user when the pipeline is missing or broken, and record the `E1`, `E3` and `D1` verdicts in `docs/04-operations/platform-readiness.yaml`.

## Step 6 — Set up observability

Breadcrumb: `number: 6`, `name: "Set up observability"`.

HITL requires two observability layers: **application observability** (logs, metrics, tracing,
alerting) and **agentic observability** (session logs, token cost). Both must be in place before
the first Tier 2 change is deployed.

**Read [observability-survey.md](observability-survey.md) and perform every step in it** — the
signal-by-signal survey, the severity table, and the required `F1` record in the readiness
register. An unrecorded gap is invisible to the roadmap and the deploy gate.

## Step 7 — Identify priority components for documentation

Breadcrumb: `number: 7`, `name: "Priority docs"`.

Ask: "Which components are most critical and most likely to change in the near term? List up to three."

For each component:
- Say: "I'll generate an HLD and LLD for [component]. Run `/hitl:dev-generate-docs` or I can do it now — which do you prefer?"
- If they want it now, run `/hitl:dev-generate-docs` for that component.
- Note: this is incremental — you do not need to document everything before starting work.

**The data layer.** Nothing above records what the data means or where it lives; once the manifest is confirmed, `/hitl:dev-map-data-layer` builds that from evidence into `docs/02-design/data/`. Optional, off until run; say this once here and never ask again.

## Step 8 — Seed the registries

Breadcrumb: `number: 8`, `name: "Seed registries"`.

Both registries and the PRD shell must exist before `/hitl:dev-practices` first runs. **Read [seed-registries.md](seed-registries.md) and perform every part of it**: the test registry, the incident registry and the product baseline (`docs/01-product/prd.md`, personas only, never a retroactive spec of existing behaviour).

## Step 9 — Build Graphify knowledge graph (optional)

Breadcrumb: `number: 9`, `name: "Graphify"`.

Run `graphify --version`. **If installed, read [graphify.md](graphify.md) and run its commands** (build the graph, install the commit hook, commit the output). If not installed, say "Graphify not found — skipping. Install it when convenient with `uv tool install graphifyy && graphify claude install`, then run `graphify .` in this repo. HITL skills fall back gracefully without it." and continue to Step 10.

## Step 10 — Create your first change issue

Breadcrumb: `number: 10`, `name: "Create issue"`.

Ask: "What's the first change you want to make now that this project is onboarded?"
- Run: `gh issue create --title "[change description]" --body "First tracked change after HITL brownfield onboarding."`
- Show the issue URL.

## Step 11 — Confirm ready

Breadcrumb: `number: 11`, `name: "Confirm ready"`.

**Before the closing message, exclude persona profiles from git.** `.hitl/people/` holds descriptions of named colleagues; committed, they land in PR diffs and stay in history. A plugin-installed team never runs `init-project.sh`, so the rule is added here.

```bash
GITIGNORE=".gitignore"
if ! grep -q "^\.hitl/people/" "$GITIGNORE" 2>/dev/null; then
  printf '\n# HITL persona profiles — descriptions of people. Local unless your team decides otherwise.\n.hitl/people/\n' >> "$GITIGNORE"
fi
git check-ignore -q .hitl/people/ 2>/dev/null \
  && echo "✓ .gitignore: .hitl/people/ excluded" \
  || echo "COULD NOT exclude .hitl/people/: say so before any profile is written here."
```

**Release notice and star, once per person, default no.** HITL has no other way to tell anyone a new version exists. The script decides whether to ask; nothing is posted without a yes.

```bash
PLUGIN_ROOT=$(python3 -c "import json,os,sys;d=json.load(open(os.path.expanduser('~/.claude/plugins/installed_plugins.json')));[print(i['installPath']) or sys.exit(0) for i in d.get('plugins',{}).get('hitl@hitl',[]) if os.path.isfile(os.path.join(i.get('installPath',''),'.claude-plugin/plugin.json'))]" 2>/dev/null)
RN="$PLUGIN_ROOT/shared/tools/hitl-onboarding/release_notice.py"
if [[ -f "$RN" ]]; then python3 "$RN" state; else echo "release_notice.py is not in this build: skipping."; fi
```

The first line of the output is the verdict. On `already-answered` or `gh-logged-out`, say the second line to the person and move on. On `ask`, put question 1 in front of the person word for word and wait; then question 2 and wait. An empty answer is no. Then record both answers: `python3 "$RN" record --notice <yes|no> --star <yes|no|skipped>`. If the first answer was yes, show the output of `python3 "$RN" body` (the exact comment) and only then run `python3 "$RN" post --confirmed`. If the second was yes, run `python3 "$RN" star --confirmed`.

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

If HITL helped, this is what to send someone:

```
claude plugin marketplace add pappar/hitl-claude-plugin
claude plugin install hitl@hitl
```
The walkthrough is at https://prasad-apparaju.github.io/hitl-dev-platform/

---
