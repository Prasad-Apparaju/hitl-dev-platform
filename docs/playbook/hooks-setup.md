# Hooks Setup — Enforcing LLD Existence Before Code Writes

Claude Code hooks are shell commands that fire at specific points in Claude's workflow. This guide sets up the `PreToolUse` hook that blocks source file writes when no LLD exists for the target component. It is the lightest-weight enforcement layer available.

**What it does:** Before Claude writes or edits any file in your source directories, the hook checks whether the system manifest has a LLD entry for that file's domain. If not, the write is blocked and the developer is told to create the LLD first.

**What it does not do:** It cannot verify Claude read the LLD. It cannot check that generated code matches the LLD. Use `/review-lld-adherence` for that.

---

## Setup

### Step 1 — Copy the hook script

Copy `scripts/check-lld-exists.sh` into your project:

```bash
cp /path/to/hitl-dev-platform/scripts/check-lld-exists.sh .claude/hooks/
chmod +x .claude/hooks/check-lld-exists.sh
```

### Step 2 — Add the hook to `.claude/settings.json`

Create or update `.claude/settings.json` in your project root:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "bash .claude/hooks/check-lld-exists.sh \"$CLAUDE_TOOL_INPUT_PATH\""
          }
        ]
      }
    ]
  }
}
```

The `matcher` fires on both `Edit` (modifying an existing file) and `Write` (creating a new file).

### Step 3 — Configure your source directories

Edit `scripts/check-lld-exists.sh` and set `SOURCE_DIRS` to match your project layout:

```bash
# Directories that contain implementation code (not docs, not tests)
SOURCE_DIRS=("app/" "src/" "lib/")
```

Files outside these directories (docs, tests, config, scripts) are not checked.

### Step 4 — Verify it works

Try editing a source file for a domain that has no LLD in your manifest:

```bash
# In Claude Code, ask Claude to edit a file with no LLD
# You should see the hook block it with a clear message
```

---

## How the hook works

```bash
FILE=$1                          # the file Claude is trying to write

# Skip if not a source file
if not in SOURCE_DIRS: exit 0   # allow

# Look up domain in system-manifest.yaml
DOMAIN=$(lookup_domain $FILE docs/system-manifest.yaml)

if DOMAIN == "unknown":
    echo "⚠️  BLOCKED: $FILE is not mapped to any domain in docs/system-manifest.yaml"
    echo "   Add this file to a domain entry before writing code."
    exit 1                       # blocks the write

LLD_PATH=$(lookup_lld $DOMAIN docs/system-manifest.yaml)

if LLD_PATH == "" or not exists:
    echo "⚠️  BLOCKED: No LLD found for domain '$DOMAIN'"
    echo "   The architect must create the LLD at $LLD_PATH before code is written."
    exit 1                       # blocks the write

exit 0                           # allow — LLD exists
```

Exit code `0` = allow the write. Any non-zero exit = block the write and show the message.

---

## Adjusting strictness

The hook has two modes, set via `HOOK_MODE` in the script:

| Mode | Behaviour |
|---|---|
| `warn` | Prints the warning but allows the write. Useful during initial adoption. |
| `block` (default) | Blocks the write. Enforces the rule hard. |

Start with `warn` when rolling out to the team. Switch to `block` once the manifest and LLDs are complete for your active domains.

---

## Limitations

- The hook checks for LLD **existence**, not LLD **quality**. A one-line LLD passes the check.
- The hook fires on file path, not on component semantics. If a file is mapped to the wrong domain in the manifest, the wrong LLD is checked.
- A developer can bypass the hook by running `git` commands directly outside Claude Code. Hooks only fire inside Claude Code sessions.
- The manifest must be kept up to date as new files are added. Run `/check-conventions --only manifest` periodically to catch drift.

---

## Adding the hook to CI (optional belt-and-suspenders)

To catch any code that bypassed the hook, add a CI check that verifies every source file in a PR is mapped to a domain with an LLD:

```yaml
# ci/check-lld-coverage.yml
- name: Check LLD coverage
  run: python tools/manifest-drift/check_manifest_drift.py --source-dirs app/ src/ --check-lld-exists
```

This catches bypasses but runs after the fact (on PR) rather than preventing them (at write time).
