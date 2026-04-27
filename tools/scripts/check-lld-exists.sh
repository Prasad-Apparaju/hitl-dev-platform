#!/usr/bin/env bash
# PreToolUse hook — blocks source file writes when no LLD exists for the component.
#
# Called by Claude Code before Edit or Write tool calls.
# Usage: check-lld-exists.sh <file-path>
#
# Exit 0 = allow the write.
# Exit 1 = block the write (message is shown to the developer in Claude Code).

set -euo pipefail

FILE="${1:-}"
MANIFEST="docs/system-manifest.yaml"

# --- Configuration -----------------------------------------------------------
# Directories containing implementation code. Files outside these are not checked.
SOURCE_DIRS=("app/" "src/" "lib/")

# warn  = print warning but allow the write (use during initial rollout)
# block = block the write (use once manifest + LLDs are complete for active domains)
HOOK_MODE="${LLD_HOOK_MODE:-block}"

# -----------------------------------------------------------------------------

# No file argument — allow (shouldn't happen, but be safe)
if [ -z "$FILE" ]; then
  exit 0
fi

# Not a source file — allow
in_source_dir=false
for dir in "${SOURCE_DIRS[@]}"; do
  if [[ "$FILE" == ${dir}* ]]; then
    in_source_dir=true
    break
  fi
done

if [ "$in_source_dir" = false ]; then
  exit 0
fi

# Manifest doesn't exist yet — warn but allow (bootstrap case)
if [ ! -f "$MANIFEST" ]; then
  echo "⚠️  WARNING: docs/system-manifest.yaml not found."
  echo "   LLD enforcement is inactive. Create the manifest to enable it."
  exit 0
fi

# Look up which domain owns this file
# Requires python3 + pyyaml: pip install pyyaml
DOMAIN=$(python3 - "$FILE" "$MANIFEST" <<'PYEOF'
import sys, yaml

file_path = sys.argv[1]
manifest_path = sys.argv[2]

with open(manifest_path) as f:
    manifest = yaml.safe_load(f)

domains = manifest.get("domains", {})
for domain_name, domain_data in domains.items():
    files = domain_data.get("files", [])
    for f in files:
        if file_path.startswith(f) or file_path == f:
            print(domain_name)
            sys.exit(0)

print("unknown")
PYEOF
)

if [ "$DOMAIN" = "unknown" ]; then
  MSG="⚠️  BLOCKED: '$FILE' is not mapped to any domain in $MANIFEST.
   Add this file to a domain entry in the manifest before writing code.
   See: docs/playbook/hooks-setup.md"

  if [ "$HOOK_MODE" = "warn" ]; then
    echo "$MSG"
    echo "   (Running in warn mode — write allowed. Set LLD_HOOK_MODE=block to enforce.)"
    exit 0
  else
    echo "$MSG"
    exit 1
  fi
fi

# Look up the LLD path for this domain
LLD_PATH=$(python3 - "$DOMAIN" "$MANIFEST" <<'PYEOF'
import sys, yaml

domain_name = sys.argv[1]
manifest_path = sys.argv[2]

with open(manifest_path) as f:
    manifest = yaml.safe_load(f)

domain = manifest.get("domains", {}).get(domain_name, {})
lld = domain.get("lld", "")
print(lld)
PYEOF
)

if [ -z "$LLD_PATH" ]; then
  MSG="⚠️  BLOCKED: Domain '$DOMAIN' has no 'lld:' entry in $MANIFEST.
   The architect must add an lld path to the '$DOMAIN' domain entry.
   See: docs/playbook/hooks-setup.md"

  if [ "$HOOK_MODE" = "warn" ]; then
    echo "$MSG"
    echo "   (Running in warn mode — write allowed.)"
    exit 0
  else
    echo "$MSG"
    exit 1
  fi
fi

if [ ! -f "$LLD_PATH" ]; then
  MSG="⚠️  BLOCKED: LLD file '$LLD_PATH' for domain '$DOMAIN' does not exist.
   The architect must create this LLD before code can be written for this domain.
   File being blocked: $FILE
   See: docs/playbook/hooks-setup.md"

  if [ "$HOOK_MODE" = "warn" ]; then
    echo "$MSG"
    echo "   (Running in warn mode — write allowed.)"
    exit 0
  else
    echo "$MSG"
    exit 1
  fi
fi

# LLD exists — allow the write
exit 0
