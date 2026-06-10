# Changelog

All notable changes to the HITL plugin are documented here.

---

## [1.0.2] — 2026-06-09

### Added

**`/hitl:update` skill** — update the plugin from inside Claude Code without touching a terminal.

Running `/hitl:update` will:
1. Locate the plugin installation from `~/.claude/settings.json`
2. Pull the latest changes (`git pull`)
3. Show the version change and a summary of what was updated
4. Re-wire `.hitl/hooks/` if they are missing or point to the wrong path
5. Prompt you to restart Claude Code

### Fixed

**README corrections:**

- Install and update instructions now clearly separated — install once with the marketplace commands, update thereafter with `/hitl:update`. Explicit note added not to re-run install commands to update.
- Stale command names in the install table corrected: `dev-start-prd/brownfield/migration` → `start-prd/brownfield/migration`
- Removed two phantom Architect commands that were listed but never existed: `/hitl:architect-review-design`, `/hitl:architect-verify-traceability`
- Removed two phantom Ops commands: `/hitl:ops-review-release`, `/hitl:ops-monitor-canary`. Replaced with actual ops commands.

### Upgrade guide — 1.0.1 → 1.0.2

Pull once manually (this is the last time):

```bash
cd /path/to/hitl-dev-platform
git pull
```

Restart Claude Code. From now on, just run `/hitl:update` whenever you want to upgrade.

---

## [1.0.1] — 2026-06-09

### Fixed

**Hook wiring now works for plugin users without cloning the repo.**

Previously, hooks were defined in `plugin.json` and ran from the plugin directory. This caused two failures:
- Scripts could not find `.hitl/current-change.yaml` (which lives in the user's project, not the plugin)
- On machines where the plugin path differed from the path baked into `.claude/settings.json`, every hook fired a "No such file or directory" error

**Windows / WSL compatibility fixes** — hook scripts now work correctly when Claude Code runs inside WSL on Windows.

- `welcome.sh`, `sync-step-to-issue.sh`: replaced hardcoded `/tmp/` paths with `${TMPDIR:-${TMP:-/tmp}}`, which resolves correctly on macOS, Linux, WSL, and Git Bash
- `write-session-summary.sh`: replaced `echo -e` with `printf` — portable across all shells including those on Windows

### What changed

| File | Change |
|---|---|
| `ai/claude/plugin/plugin.json` | Removed `"hooks"` entry — plugin-level hooks are the wrong mechanism |
| `ai/claude/start-prd/SKILL.md` | Added Step 0: auto-wires `.hitl/hooks/` and `.claude/settings.json` |
| `ai/claude/start-brownfield/SKILL.md` | Added Step 0: same hook wiring |
| `ai/claude/start-migration/SKILL.md` | Added Step 0: same hook wiring |
| `.claude/settings.json` | Removed hardcoded `/Users/Prasad_1/…` path prefix from all hook commands |
| `ai/claude/hooks/welcome.sh` | Replaced `/tmp` hardcode with `${TMPDIR:-${TMP:-/tmp}}` |
| `ai/claude/hooks/sync-step-to-issue.sh` | Same `/tmp` fix |
| `ai/claude/hooks/write-session-summary.sh` | Replaced `echo -e` with portable `printf` |

### How hooks now work

Each start skill (`/hitl:start-prd`, `/hitl:start-brownfield`, `/hitl:start-migration`) includes a **Step 0** that runs once per project:

1. Discovers the plugin installation path from `~/.claude/settings.json`
2. Creates `.hitl/hooks/*.sh` wrapper scripts in the user's project — each wrapper delegates to the real script in the plugin via `${HITL_PLATFORM_ROOT:-<discovered-path>}`
3. Creates `.claude/settings.json` in the user's project pointing to those wrappers

This is the same pattern `init-project.sh` used, now delivered automatically through the plugin.

---

## Upgrade guide — 1.0.0 → 1.0.1

### Everyone

Pull the latest plugin:

```bash
cd /path/to/hitl-dev-platform
git pull
```

Restart Claude Code so the updated `plugin.json` is reloaded.

### New projects (not yet initialized)

No further action needed. Run your start skill as normal — Step 0 will wire the hooks automatically.

### Existing projects (already running the HITL workflow)

Your project does not have `.hitl/hooks/` wrappers yet. Create them now by running the appropriate start skill — it is **idempotent** and will skip any setup that is already in place:

```
/hitl:start-prd
```
or
```
/hitl:start-brownfield
```
or
```
/hitl:start-migration
```

Step 0 will detect that `.hitl/hooks/` is missing, wire everything up, and prompt you to restart Claude Code. After the restart, hooks will fire correctly on every edit.

### Windows / WSL users

No special steps required beyond the above. The `/tmp` path fix and `printf` fix are included in this release and work automatically.

---

## [1.0.0] — initial release
